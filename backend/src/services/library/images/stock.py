import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy import ColumnElement
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.search.vector import cosine_distance
from utils.db.models import ImageSource, Innovation, InnovationImage
from utils.logging import logger

from .pictures import Prepared
from .storage import Chosen, store

ORIGINALS = tuple(source.value for source in ImageSource)


@dataclass(frozen=True, slots=True)
class Target:
    id: uuid.UUID
    slug: str
    category_slug: str
    embedding: list[float] | None


def target(innovation: Innovation) -> Target:
    embedding = innovation.embedding
    return Target(
        id=innovation.id,
        slug=innovation.slug,
        category_slug=innovation.category_slug,
        embedding=None if embedding is None else [float(v) for v in embedding],
    )


def in_pool() -> list[ColumnElement[bool]]:
    return [
        col(Innovation.image_version).is_not(None),
        col(Innovation.image_source).in_(ORIGINALS),
    ]


def spread(slug: str, size: int) -> int:
    return int.from_bytes(hashlib.sha256(slug.encode()).digest()[:8]) % size


async def pick(session: AsyncSession, item: Target) -> uuid.UUID | None:
    pool = select(Innovation.id).where(*in_pool(), col(Innovation.id) != item.id)
    for scope in (
        pool.where(col(Innovation.category_slug) == item.category_slug),
        pool,
    ):
        if item.embedding is not None:
            nearest = (
                await session.exec(
                    scope.where(col(Innovation.embedding).is_not(None))
                    .order_by(
                        cosine_distance(Innovation.embedding, item.embedding),
                        col(Innovation.slug),
                    )
                    .limit(1)
                )
            ).first()
            if nearest is not None:
                return nearest
        ids = list((await session.exec(scope.order_by(col(Innovation.slug)))).all())
        if ids:
            return ids[spread(item.slug, len(ids))]
    return None


async def is_pool_picture(session: AsyncSession, innovation_id: uuid.UUID) -> bool:
    found = await session.exec(
        select(Innovation.id).where(*in_pool(), col(Innovation.id) == innovation_id)
    )
    return found.first() is not None


async def reuse(
    session: AsyncSession, target_id: uuid.UUID, donor_id: uuid.UUID
) -> int:
    donor = await session.get(InnovationImage, donor_id)
    if donor is None:
        message = f"innovation {donor_id} has no stored picture"
        raise LookupError(message)
    chosen = Chosen(
        source=donor.source,
        prepared=Prepared(
            image=donor.image, card=donor.card, width=donor.width, height=donor.height
        ),
        alt=donor.alt,
        source_url=donor.source_url,
        prompt=donor.prompt,
        model=donor.model,
        reused=True,
    )
    return await store(session, target_id, chosen)


async def give_stock(session: AsyncSession, item: Target) -> bool:
    donor = await pick(session, item)
    if donor is None:
        logger.warning("images: the pool is empty, %s has no picture", item.slug)
        return False
    await reuse(session, item.id, donor)
    logger.info("images: %s reuses the picture of %s", item.slug, donor)
    return True


async def fill_missing(session: AsyncSession) -> int:
    missing = (
        await session.exec(
            select(Innovation)
            .where(col(Innovation.image_version).is_(None))
            .order_by(col(Innovation.slug))
        )
    ).all()
    todo = [target(innovation) for innovation in missing]
    filled = 0
    for item in todo:
        if not await give_stock(session, item):
            break
        filled += 1
    return filled
