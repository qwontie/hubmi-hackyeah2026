from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from api.limits import rate_limit
from services.ai import AiBudgetExceededError, AiUnavailableError
from services.needs import TextRejectedError, match_need
from services.tester.repository import vote_counts

from .common import categories_by_slug, translate
from .schemas import (
    ClusterRef,
    InnovationSummary,
    MatchIn,
    MatchItem,
    MatchOut,
    NeedRef,
)

router = APIRouter(route_class=DishkaRoute)
limiter = rate_limit("match", per_minute=10, per_day=100)


@router.post("", dependencies=[Depends(limiter)])
async def match(body: MatchIn, session: FromDishka[AsyncSession]) -> MatchOut:
    try:
        outcome = await match_need(session, body.text, powiat=body.powiat)
    except (TextRejectedError, AiUnavailableError, AiBudgetExceededError) as e:
        raise translate(e) from e
    categories = await categories_by_slug(session)
    votes = await vote_counts(session, [r.hit.innovation.id for r in outcome.results])
    cluster = outcome.cluster
    return MatchOut(
        need=NeedRef(
            id=outcome.need.id,
            number=outcome.need.number or 0,
            edit_token=outcome.token,
        ),
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
    )
