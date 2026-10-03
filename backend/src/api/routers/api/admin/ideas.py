import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from api.security import AdminPerson
from services.dialogue import service
from services.dialogue.schemas import AdminMessage, ReplyBody
from services.mail import Mailer
from utils.db.models import Idea

router = APIRouter(route_class=DishkaRoute)

reply_limit = rate_limit("admin_idea_reply", per_minute=30, per_day=1000)

IDEA_MISSING = "Nie znaleziono pomysłu."


async def existing(session: AsyncSession, idea_id: uuid.UUID) -> Idea:
    idea = await session.get(Idea, idea_id)
    if idea is None:
        raise not_found(IDEA_MISSING)
    return idea


@router.get("/{idea_id}/messages")
async def messages(
    idea_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> list[AdminMessage]:
    return await service.thread_for_admin(session, await existing(session, idea_id))


@router.post("/{idea_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(idea_id: uuid.UUID, session: FromDishka[AsyncSession]) -> None:
    await service.mark_read(session, await existing(session, idea_id))


@router.post(
    "/{idea_id}/reply",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(reply_limit)],
)
async def reply(
    idea_id: uuid.UUID,
    body: ReplyBody,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> AdminMessage:
    idea = await existing(session, idea_id)
    return await service.reply(session, idea, admin, body.body, mailer)
