from collections import Counter

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel.ext.asyncio.session import AsyncSession

from api.limits import rate_limit
from services.needs import SearchOutcome, search_need
from services.tester.repository import vote_counts
from utils.db import session_scope
from utils.db.models import SearchLog
from utils.logging import logger

from .common import categories_by_slug
from .schemas import ClusterRef, InnovationSummary, MatchIn, MatchItem, MatchOut

router = APIRouter(route_class=DishkaRoute)
limiter = rate_limit("match", per_minute=10, per_day=100)


def _category(outcome: SearchOutcome) -> str | None:
    counts = Counter[str]()
    for rank, result in enumerate(outcome.results):
        counts[result.hit.innovation.category_slug] += len(outcome.results) - rank
    return counts.most_common(1)[0][0] if counts else None


async def log_search(outcome: SearchOutcome) -> None:
    entry = SearchLog(
        outcome=outcome.reason or "ok",
        category_slug=_category(outcome),
        slugs=[r.hit.innovation.slug for r in outcome.results],
        scores=[r.hit.score for r in outcome.results],
        degraded=outcome.degraded,
    )
    try:
        async with session_scope() as log:
            log.add(entry)
            await log.commit()
    except SQLAlchemyError:
        logger.exception("search log not stored")


@router.post("", dependencies=[Depends(limiter)])
async def match(body: MatchIn, session: FromDishka[AsyncSession]) -> MatchOut:
    outcome = await search_need(session, body.text)
    await log_search(outcome)
    categories = await categories_by_slug(session)
    votes = await vote_counts(session, [r.hit.innovation.id for r in outcome.results])
    cluster = outcome.cluster
    return MatchOut(
        need=None,
        results=[
            MatchItem(
                innovation=InnovationSummary.build(r.hit.innovation, categories, votes),
                score=r.hit.score,
                reason=r.reason,
            )
            for r in outcome.results
        ],
        similar_count=outcome.similar_count,
        cluster=ClusterRef(id=cluster.id, title=cluster.title, size=cluster.size)
        if cluster
        else None,
        degraded=outcome.degraded,
        reason=outcome.reason,
    )
