import uuid
from collections import OrderedDict
from collections.abc import Collection
from dataclasses import dataclass

from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.ai import embed_query
from utils.db.models.innovation import Innovation, InnovationStatus

from .text import keyword_terms
from .vector import cosine_distance

SHORT_QUERY_TERMS = 3
SHORT_KEYWORD_BONUS = 0.12
LONG_KEYWORD_BONUS = 0.04
CANDIDATES = 20
QUERY_CACHE_SIZE = 512


@dataclass(slots=True)
class Hit:
    innovation: Innovation
    score: float
    similarity: float
    keyword: float


_query_cache: OrderedDict[str, list[float]] = OrderedDict()


async def cached_query_embedding(text: str, *, kind: str) -> list[float]:
    key = " ".join(text.lower().split())
    if key in _query_cache:
        _query_cache.move_to_end(key)
        return _query_cache[key]
    vector = await embed_query(text, kind=kind)
    _query_cache[key] = vector
    if len(_query_cache) > QUERY_CACHE_SIZE:
        _query_cache.popitem(last=False)
    return vector


async def hybrid_search(
    session: AsyncSession,
    text: str,
    vector: list[float],
    *,
    limit: int = 10,
    category: str | None = None,
) -> list[Hit]:
    published = col(Innovation.status) == InnovationStatus.PUBLISHED
    filters = [published]
    if category:
        filters.append(col(Innovation.category_slug) == category)
    distance = cosine_distance(Innovation.embedding, vector)

    ids = set(
        (
            await session.exec(
                select(Innovation.id)
                .where(*filters, col(Innovation.embedding).is_not(None))
                .order_by(distance)
                .limit(CANDIDATES)
            )
        ).all()
    )
    keyword_ranks: dict[uuid.UUID, float] = {}
    terms = keyword_terms(text)
    if terms:
        tsquery = func.to_tsquery("simple", " | ".join(terms))
        rank = func.ts_rank_cd(col(Innovation.search), tsquery, 32)
        rows = (
            await session.exec(
                select(Innovation.id, rank)
                .where(*filters, col(Innovation.search).op("@@")(tsquery))
                .order_by(rank.desc())
                .limit(CANDIDATES)
            )
        ).all()
        keyword_ranks = {row[0]: float(row[1]) for row in rows}
        ids.update(keyword_ranks)
    if not ids:
        return []

    similarity = (1 - distance).label("similarity")
    rows = (
        await session.exec(
            select(Innovation, similarity).where(col(Innovation.id).in_(ids))
        )
    ).all()
    bonus = (
        SHORT_KEYWORD_BONUS if len(terms) <= SHORT_QUERY_TERMS else LONG_KEYWORD_BONUS
    )
    hits = []
    for innovation, sim in rows:
        keyword = keyword_ranks.get(innovation.id, 0.0)
        sim_value = float(sim or 0.0)
        score = sim_value + bonus * keyword
        hits.append(
            Hit(
                innovation=innovation,
                score=round(min(max(score, 0.0), 1.0), 4),
                similarity=sim_value,
                keyword=keyword,
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]


async def search_query(
    session: AsyncSession, text: str, *, limit: int = 10, category: str | None = None
) -> list[Hit]:
    vector = await cached_query_embedding(text, kind="embed_search")
    return await hybrid_search(session, text, vector, limit=limit, category=category)


async def nearest_innovations(
    session: AsyncSession,
    vector: list[float],
    *,
    limit: int = 5,
    exclude_ids: Collection[uuid.UUID] = (),
) -> list[tuple[Innovation, float]]:
    distance = cosine_distance(Innovation.embedding, vector)
    query = select(Innovation, (1 - distance).label("similarity")).where(
        col(Innovation.status) == InnovationStatus.PUBLISHED,
        col(Innovation.embedding).is_not(None),
    )
    if exclude_ids:
        query = query.where(col(Innovation.id).not_in(list(exclude_ids)))
    rows = (await session.exec(query.order_by(distance).limit(limit))).all()
    return [(innovation, float(similarity)) for innovation, similarity in rows]
