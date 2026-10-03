import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Header, Query, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import ApiError, not_found
from api.limits import client_ip, rate_limit
from api.security import admin_from_secret
from services.bus import bus
from services.dialogue.service import idea_for_token, token_opens
from services.kreator import repository
from services.visual import image_key_matches
from services.visual.service import (
    LimitReachedError,
    Visualisation,
    generate,
    stored_image,
)
from utils.db.models import AdminRole
from utils.env import env

from .common import ReadLimited, ai_guard

router = APIRouter(route_class=DishkaRoute, tags=["kreator"])

visual_limit = rate_limit("idea_visual", per_minute=2, per_day=5)

IDEA_MISSING = "Nie znaleziono tego pomysłu."
IMAGE_MISSING = "Nie ma jeszcze wizualizacji tego pomysłu."
LIMIT_MESSAGE = "Ten pomysł ma już 3 wizualizacje. Więcej nie możemy przygotować."
PUBLIC_CACHE = "public, max-age=31536000, immutable"
PRIVATE_CACHE = "private, max-age=3600"
STALE_CACHE = "private, no-cache"

IdeaToken = Annotated[str | None, Header(alias="X-Idea-Token", max_length=200)]
ImageKey = Annotated[str | None, Query(max_length=64, pattern=r"^[A-Za-z0-9_-]*$")]
Version = Annotated[int | None, Query(ge=1, le=1000)]


def limit_reached() -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, "visualisation_limit", LIMIT_MESSAGE)


@router.post("/ideas/{idea_id}/visualisation", status_code=status.HTTP_201_CREATED)
async def create_visualisation(
    idea_id: uuid.UUID,
    request: Request,
    session: FromDishka[AsyncSession],
    x_idea_token: IdeaToken = None,
) -> Visualisation:
    idea = await idea_for_token(session, idea_id, x_idea_token)
    if idea is None:
        raise not_found(IDEA_MISSING)
    if idea.visualisation_count >= repository.MAX_VISUALISATIONS:
        raise limit_reached()
    visual_limit.check(client_ip(request))
    async with ai_guard():
        try:
            result = await generate(session, idea)
        except LimitReachedError:
            raise limit_reached() from None
    bus.publish("idea.updated", await repository.admin_out(session, idea))
    return result


async def may_view(
    request: Request, session: AsyncSession, idea_id: uuid.UUID, token: str | None
) -> bool:
    idea = await repository.get(session, idea_id)
    if idea is None:
        return False
    if idea.status in repository.PUBLIC_STATUSES or token_opens(idea, token):
        return True
    viewer = await admin_from_secret(request.cookies.get(env.auth.cookie_name))
    return viewer is not None and viewer.role == AdminRole.ADMIN


@router.get("/ideas/{idea_id}/visualisation.png", response_class=Response)
async def visualisation_image(  # noqa: PLR0913
    *,
    idea_id: uuid.UUID,
    request: Request,
    session: FromDishka[AsyncSession],
    _: ReadLimited,
    v: Version = None,
    key: ImageKey = None,
    x_idea_token: IdeaToken = None,
) -> Response:
    stored = await stored_image(session, idea_id)
    if stored is None:
        raise not_found(IMAGE_MISSING)
    idea = await repository.get(session, idea_id)
    public = idea is not None and idea.status in repository.PUBLIC_STATUSES
    allowed = image_key_matches(idea_id, stored.version, key) or await may_view(
        request, session, idea_id, x_idea_token
    )
    if not allowed:
        raise not_found(IMAGE_MISSING)
    etag = f'"{idea_id}-{stored.version}"'
    if v != stored.version:
        cache = STALE_CACHE
    else:
        cache = PUBLIC_CACHE if public else PRIVATE_CACHE
    headers = {"Cache-Control": cache, "ETag": etag, "Vary": "Cookie, X-Idea-Token"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return Response(content=stored.image, media_type=stored.mime_type, headers=headers)
