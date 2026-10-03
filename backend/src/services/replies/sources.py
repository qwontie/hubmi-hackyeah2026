import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import Innovation, InnovationStatus, MatchResult, Need

from .schemas import EarlierAnswer

MATCH_LIMIT = 3
EARLIER_LIMIT = 3
MIN_SIMILARITY = 0.7
EXCERPT = 200
TEXT_LIMIT = 900

EARLIER_SQL = text(
    """
    select * from (
    select distinct on (n.id)
        n.number, n.text, m.body, m.sent_at,
        1 - (n.embedding <=> cast(:embedding as vector)) as similarity,
        exists (
            select 1 from demo_record d
            where d.row_id in (m.id, n.id) and d.kind in ('message', 'need')
        ) as demo
    from message m
    join need n on n.id = m.need_id
    where m.direction = 'to_author'
        and m.admin_id is not null
        and m.expert_name is null
        and n.id <> :need_id
        and n.embedding is not null
    order by n.id, m.sent_at
    ) found
    where similarity >= :floor
    order by similarity desc
    limit :limit
    """
)


@dataclass(frozen=True, slots=True)
class Matched:
    innovation: Innovation
    reason: str


async def matched(session: AsyncSession, need_id: uuid.UUID) -> list[Matched]:
    rows = (
        await session.exec(
            select(Innovation, MatchResult)
            .join(MatchResult, col(MatchResult.innovation_id) == Innovation.id)
            .where(
                col(MatchResult.need_id) == need_id,
                col(Innovation.status) == InnovationStatus.PUBLISHED,
            )
            .order_by(col(MatchResult.rank))
        )
    ).all()
    found: dict[uuid.UUID, Matched] = {}
    for innovation, match in rows:
        if innovation.id not in found:
            found[innovation.id] = Matched(innovation, match.reason)
    return list(found.values())[:MATCH_LIMIT]


def excerpt(value: str, limit: int = EXCERPT) -> str:
    flat = " ".join(value.split())
    if len(flat) <= limit:
        return flat
    return flat[:limit].rsplit(" ", 1)[0] + "…"


async def earlier_answers(session: AsyncSession, need: Need) -> list[EarlierAnswer]:
    if need.embedding is None:
        return []
    connection = await session.connection()
    rows = (
        await connection.execute(
            EARLIER_SQL,
            {
                "embedding": str(list(need.embedding)),
                "need_id": need.id,
                "floor": MIN_SIMILARITY,
                "limit": EARLIER_LIMIT,
            },
        )
    ).all()
    return [
        EarlierAnswer(
            need_number=row.number,
            need_excerpt=excerpt(row.text),
            body=row.body,
            sent_at=row.sent_at,
            similarity=round(float(row.similarity), 3),
            demo=bool(row.demo),
        )
        for row in rows
    ]
