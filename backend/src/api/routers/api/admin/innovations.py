from typing import Annotated, Literal

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Path, Query, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.security import AdminPerson
from services.library import service
from services.library.images.service import stored_image
from services.library.schemas import (
    AdminInnovationDetail,
    InnovationChanges,
    InnovationCreate,
    InnovationPage,
    InnovationQuery,
    PictureChoice,
    PoolPicture,
)
from utils.db.models import InnovationStatus

router = APIRouter(route_class=DishkaRoute)
IMAGE_MISSING = "Ta innowacja nie ma jeszcze obrazka."
IMMUTABLE_CACHE = "private, max-age=31536000, immutable"
SHORT_CACHE = "private, max-age=60"


@router.get("")
async def list_innovations(
    query: Annotated[InnovationQuery, Query()], session: FromDishka[AsyncSession]
) -> InnovationPage:
    items, total = await service.list_innovations(session, query)
    return InnovationPage(
        items=items, total=total, page=query.page, per_page=query.per_page
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_innovation(
    body: InnovationCreate, admin: AdminPerson, session: FromDishka[AsyncSession]
) -> AdminInnovationDetail:
    return await service.create(session, admin, body)


@router.get("/picture-pool")
async def picture_pool(session: FromDishka[AsyncSession]) -> list[PoolPicture]:
    return await service.picture_pool(session)


@router.get("/{slug}")
async def innovation_detail(
    slug: str, session: FromDishka[AsyncSession]
) -> AdminInnovationDetail:
    innovation, category = await service.find(session, slug)
    return service.detail(innovation, category)


@router.patch("/{slug}")
async def update_innovation(
    slug: str,
    body: InnovationChanges,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> AdminInnovationDetail:
    return await service.update(session, admin, slug, body)


@router.post("/{slug}/publish")
async def publish(
    slug: str, admin: AdminPerson, session: FromDishka[AsyncSession]
) -> AdminInnovationDetail:
    return await service.set_status(session, admin, slug, InnovationStatus.PUBLISHED)


@router.post("/{slug}/unpublish")
async def unpublish(
    slug: str, admin: AdminPerson, session: FromDishka[AsyncSession]
) -> AdminInnovationDetail:
    return await service.set_status(session, admin, slug, InnovationStatus.DRAFT)


@router.put("/{slug}/picture")
async def set_picture(
    slug: str,
    body: PictureChoice,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> AdminInnovationDetail:
    return await service.set_picture(session, admin, slug, body)


@router.get("/{slug}/image", response_class=Response)
async def innovation_image(
    slug: Annotated[str, Path(max_length=200)],
    request: Request,
    session: FromDishka[AsyncSession],
    v: Annotated[int | None, Query(ge=1, le=100000)] = None,
    size: Annotated[Literal["full", "card"], Query()] = "full",
) -> Response:
    found = await stored_image(session, slug)
    if found is None:
        raise not_found(IMAGE_MISSING)
    image = found[1]
    etag = f'"admin-{slug}-{image.version}-{size}"'
    headers = {
        "Cache-Control": IMMUTABLE_CACHE if v == image.version else SHORT_CACHE,
        "ETag": etag,
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    content = image.card if size == "card" else image.image
    return Response(content=content, media_type=image.mime_type, headers=headers)
