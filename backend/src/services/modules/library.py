import uuid
from collections.abc import Sequence

from pydantic import BaseModel
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import Innovation, InnovationStatus


class InnovationRef(BaseModel):
    slug: str
    title: str

    @classmethod
    def of(cls, innovation: Innovation) -> "InnovationRef":
        return cls(slug=innovation.slug, title=innovation.title)


async def published_innovation(session: AsyncSession, slug: str) -> Innovation | None:
    return (
        await session.exec(
            select(Innovation).where(
                Innovation.slug == slug, Innovation.status == InnovationStatus.PUBLISHED
            )
        )
    ).first()


async def innovation_refs(
    session: AsyncSession, ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, InnovationRef]:
    if not ids:
        return {}
    rows = await session.exec(
        select(Innovation).where(col(Innovation.id).in_(set(ids)))
    )
    return {row.id: InnovationRef.of(row) for row in rows}
