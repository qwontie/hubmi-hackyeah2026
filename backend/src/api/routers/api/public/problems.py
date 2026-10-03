import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from services.kreator import repository as ideas
from services.problems import (
    ProblemFilters,
    get_problem,
    list_problems,
    problem_ideas,
    problem_innovations,
)
from services.tester.repository import vote_counts

from .common import categories_by_slug
from .schemas import InnovationSummary, Problem, ProblemDetail, ProblemPage

router = APIRouter(route_class=DishkaRoute)
limiter = rate_limit("problems", per_minute=120)
MISSING = "Nie znaleziono takiego problemu."
SLUG = r"^[a-z0-9-]+$"
NO_NUL = r"^[^\x00]*$"


@router.get("", dependencies=[Depends(limiter)])
async def problems(  # noqa: PLR0913
    *,
    session: FromDishka[AsyncSession],
    q: Annotated[
        str | None, Query(min_length=2, max_length=200, pattern=NO_NUL)
    ] = None,
    category: Annotated[str | None, Query(max_length=100, pattern=SLUG)] = None,
    powiat: Annotated[str | None, Query(max_length=60, pattern=SLUG)] = None,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProblemPage:
    filters = ProblemFilters(
        q=q.strip() if q and q.strip() else None, category=category, powiat=powiat
    )
    rows, total = await list_problems(session, filters, page=page, per_page=per_page)
    return ProblemPage(
        items=[Problem.build(row) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{problem_id}", dependencies=[Depends(limiter)])
async def problem(
    problem_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> ProblemDetail:
    row = await get_problem(session, problem_id)
    if row is None:
        raise not_found(MISSING)
    innovations = await problem_innovations(session, problem_id)
    categories = await categories_by_slug(session)
    votes = await vote_counts(session, [i.id for i in innovations])
    return ProblemDetail(
        **Problem.build(row).model_dump(),
        innovations=[
            InnovationSummary.build(i, categories, votes) for i in innovations
        ],
        ideas=[ideas.public_view(i) for i in await problem_ideas(session, problem_id)],
    )
