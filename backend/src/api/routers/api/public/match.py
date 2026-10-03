from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from api.limits import rate_limit
from services.needs import search_need
from services.tester.repository import vote_counts

from .common import categories_by_slug
from .schemas import ClusterRef, InnovationSummary, MatchIn, MatchItem, MatchOut

router = APIRouter(route_class=DishkaRoute)
limiter = rate_limit("match", per_minute=10, per_day=100)


@router.post("", dependencies=[Depends(limiter)])
async def match(body: MatchIn, session: FromDishka[AsyncSession]) -> MatchOut:
    outcome = await search_need(session, body.text)
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
