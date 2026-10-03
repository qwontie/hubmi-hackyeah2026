import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import update
from sqlmodel import col
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import Idea, IdeaVisualisation

from .image import draw
from .links import MAX_GENERATIONS, generations_left, image_url
from .prompt import image_prompt, write_scene


class Visualisation(BaseModel):
    url: str
    alt: str
    generations_used: int
    generations_left: int
    created_at: datetime


class LimitReachedError(RuntimeError):
    pass


async def reserve(session: AsyncSession, idea_id: uuid.UUID) -> int:
    result = await session.exec(
        update(Idea)
        .where(col(Idea.id) == idea_id, col(Idea.visualisation_count) < MAX_GENERATIONS)
        .values(visualisation_count=col(Idea.visualisation_count) + 1)
        .returning(col(Idea.visualisation_count))
    )
    used = result.scalar_one_or_none()
    await session.commit()
    if used is None:
        raise LimitReachedError
    return used


async def release(session: AsyncSession, idea_id: uuid.UUID) -> None:
    await session.exec(
        update(Idea)
        .where(col(Idea.id) == idea_id, col(Idea.visualisation_count) > 0)
        .values(visualisation_count=col(Idea.visualisation_count) - 1)
    )
    await session.commit()


async def generate(session: AsyncSession, idea: Idea) -> Visualisation:
    idea_id = idea.id
    used = await reserve(session, idea_id)
    try:
        await session.refresh(idea)
        scene = await write_scene(idea)
        prompt = image_prompt(scene)
        picture = await draw(prompt)
    except Exception:
        await session.rollback()
        await release(session, idea_id)
        raise
    stored = await session.get(IdeaVisualisation, idea_id)
    if stored is None:
        stored = IdeaVisualisation(
            idea_id=idea_id,
            version=used,
            image=picture.data,
            mime_type=picture.mime_type,
            prompt=prompt,
            alt=scene.alt,
            model=picture.model,
        )
    else:
        stored.version = used
        stored.image = picture.data
        stored.mime_type = picture.mime_type
        stored.prompt = prompt
        stored.alt = scene.alt
        stored.model = picture.model
        stored.created_at = datetime.now(UTC)
    idea.visualisation_version = used
    idea.visualisation_alt = scene.alt
    session.add(stored)
    session.add(idea)
    await session.commit()
    await session.refresh(stored)
    await session.refresh(idea)
    return Visualisation(
        url=image_url(idea_id, used) or "",
        alt=scene.alt,
        generations_used=used,
        generations_left=generations_left(used),
        created_at=stored.created_at,
    )


async def stored_image(
    session: AsyncSession, idea_id: uuid.UUID
) -> IdeaVisualisation | None:
    return await session.get(IdeaVisualisation, idea_id)
