import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from api.security import AdminPerson
from services.dialogue import inbox, service
from services.dialogue.schemas import (
    AdminMessage,
    AdminNeed,
    AdminNeedDetail,
    NeedPage,
    NeedQuery,
    ReplyBody,
    StatusBody,
)
from services.mail import Mailer
from utils.db.models import Need

router = APIRouter(route_class=DishkaRoute)


class NeedCounts(BaseModel):
    waiting: int
    answered: int
    closed: int
    junk: int
    total: int
    unread: int


reply_limit = rate_limit("admin_reply", per_minute=30, per_day=1000)

NEED_MISSING = "Nie znaleziono zgłoszenia."


async def existing(session: AsyncSession, need_id: uuid.UUID) -> Need:
    need = await inbox.get_need(session, need_id)
    if need is None:
        raise not_found(NEED_MISSING)
    return need


@router.get("")
async def list_needs(
    query: Annotated[NeedQuery, Query()], session: FromDishka[AsyncSession]
) -> NeedPage:
    text = query.q.strip() if query.q else ""
    filters = inbox.NeedFilters(
        status=query.status,
        cluster_id=query.cluster_id,
        powiat=query.powiat,
        category=query.category,
        nothing_fits=query.nothing_fits,
        unread=query.unread,
        has_contact=query.has_contact,
        q=text or None,
        sort=query.sort,
    )
    items, total = await inbox.list_needs(session, filters, query.page, query.per_page)
    return NeedPage(items=items, total=total, page=query.page, per_page=query.per_page)


@router.get("/counts")
async def need_counts(session: FromDishka[AsyncSession]) -> NeedCounts:
    return NeedCounts(**await inbox.counts(session))


@router.get("/{need_id}")
async def need_detail(
    need_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> AdminNeedDetail:
    return await inbox.need_detail(session, await existing(session, need_id))


@router.patch("/{need_id}")
async def update_need(
    need_id: uuid.UUID,
    body: StatusBody,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> AdminNeed:
    need = await service.set_status(
        session, await existing(session, need_id), admin, body.status
    )
    return (await inbox.build(session, [need]))[0]


@router.post("/{need_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(need_id: uuid.UUID, session: FromDishka[AsyncSession]) -> None:
    await service.mark_read(session, await existing(session, need_id))


@router.post(
    "/{need_id}/reply",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(reply_limit)],
)
async def reply(
    need_id: uuid.UUID,
    body: ReplyBody,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> AdminMessage:
    need = await existing(session, need_id)
    return await service.reply(session, need, admin, body.body, mailer)
