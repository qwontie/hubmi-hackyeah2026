import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from api.routers.api.modules.common import ai_guard
from services.dialogue import inbox
from services.replies import ReplySuggestions, cached, suggest

router = APIRouter(route_class=DishkaRoute)

suggest_limit = rate_limit("admin_reply_suggestions", per_minute=20, per_day=500)

NEED_MISSING = "Nie znaleziono zgłoszenia."


@router.get(
    "/{need_id}/reply-suggestions",
    response_model=ReplySuggestions,
    responses={status.HTTP_204_NO_CONTENT: {"description": "Not generated yet"}},
)
async def stored_reply_suggestions(
    need_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> ReplySuggestions | Response:
    need = await inbox.get_need(session, need_id)
    if need is None:
        raise not_found(NEED_MISSING)
    return cached(need) or Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{need_id}/reply-suggestions", dependencies=[Depends(suggest_limit)])
async def reply_suggestions(
    need_id: uuid.UUID, session: FromDishka[AsyncSession], *, refresh: bool = False
) -> ReplySuggestions:
    need = await inbox.get_need(session, need_id)
    if need is None:
        raise not_found(NEED_MISSING)
    stored = None if refresh else cached(need)
    if stored is not None:
        return stored
    async with ai_guard():
        return await suggest(session, need, refresh=refresh)
