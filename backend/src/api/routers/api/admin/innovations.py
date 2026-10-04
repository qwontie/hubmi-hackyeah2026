from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.security import AdminPerson
from services.library import service
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
