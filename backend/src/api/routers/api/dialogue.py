import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from services.dialogue import service
from services.dialogue.schemas import (
    AuthorMessageBody,
    PublicIdea,
    PublicIdeaThread,
    PublicMessage,
    PublicNeed,
    PublicThread,
)
from utils.db.models import Idea, Need

router = APIRouter(route_class=DishkaRoute, tags=["dialogue"])
ideas = APIRouter(route_class=DishkaRoute, tags=["dialogue"])

read_limit = rate_limit("thread_read", per_minute=120)
write_limit = rate_limit("thread_write", per_minute=5, per_day=50)

NEED_MISSING = "Nie znaleziono zgłoszenia."

IDEA_MISSING = "Nie znaleziono pomysłu."

IdeaToken = Annotated[str | None, Header(alias="X-Idea-Token", max_length=200)]
NeedToken = Annotated[str | None, Header(alias="X-Need-Token", max_length=200)]


async def opened(session: AsyncSession, need_id: uuid.UUID, token: str | None) -> Need:
    need = await service.need_for_token(session, need_id, token)
    if need is None:
        raise not_found(NEED_MISSING)
    return need


@router.get("/{need_id}/thread", dependencies=[Depends(read_limit)])
async def thread(
    need_id: uuid.UUID, session: FromDishka[AsyncSession], token: NeedToken = None
) -> PublicThread:
    need = await opened(session, need_id, token)
    return PublicThread(
        need=PublicNeed(
            id=need.id,
            number=need.number,
            text=need.text,
            status=need.status,
            created_at=need.created_at,
        ),
        messages=await service.public_messages(session, need),
        can_email=service.can_email(need),
    )


@router.post(
    "/{need_id}/messages",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(write_limit)],
)
async def write(
    need_id: uuid.UUID,
    body: AuthorMessageBody,
    session: FromDishka[AsyncSession],
    token: NeedToken = None,
) -> PublicMessage:
    need = await opened(session, need_id, token)
    return await service.author_message(session, need, body.body)


async def opened_idea(
    session: AsyncSession, idea_id: uuid.UUID, token: str | None
) -> Idea:
    idea = await service.idea_for_token(session, idea_id, token)
    if idea is None:
        raise not_found(IDEA_MISSING)
    return idea


@ideas.get("/{idea_id}/thread", dependencies=[Depends(read_limit)])
async def idea_thread(
    idea_id: uuid.UUID, session: FromDishka[AsyncSession], token: IdeaToken = None
) -> PublicIdeaThread:
    idea = await opened_idea(session, idea_id, token)
    return PublicIdeaThread(
        idea=PublicIdea(
            id=idea.id,
            number=idea.number,
            title=idea.title,
            status=idea.status,
            created_at=idea.created_at,
        ),
        messages=await service.public_messages(session, idea),
        can_email=service.can_email(idea),
    )


@ideas.post(
    "/{idea_id}/messages",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(write_limit)],
)
async def write_idea(
    idea_id: uuid.UUID,
    body: AuthorMessageBody,
    session: FromDishka[AsyncSession],
    token: IdeaToken = None,
) -> PublicMessage:
    idea = await opened_idea(session, idea_id, token)
    return await service.author_message(session, idea, body.body)
