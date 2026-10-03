from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Path, Query
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from services.ai import AiBudgetExceededError, AiUnavailableError
from services.needs import POWIATS
from services.search import search_query
from utils.db.models.innovation import Innovation, InnovationStatus

from .common import categories_by_slug, translate
from .schemas import (
    CategoryOut,
    InnovationDetail,
    InnovationPage,
    InnovationSummary,
    PowiatOut,
)

router = APIRouter(route_class=DishkaRoute)
limiter = rate_limit("library", per_minute=120)
SEARCH_LIMIT = 30
MISSING = "Nie znaleziono takiej innowacji."


@router.get("/innovations", dependencies=[Depends(limiter)])
async def list_innovations(
    session: FromDishka[AsyncSession],
    category: Annotated[str | None, Query(max_length=100)] = None,
    q: Annotated[str | None, Query(min_length=2, max_length=200)] = None,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
) -> InnovationPage:
    categories = await categories_by_slug(session)
    if q and q.strip():
        try:
            hits = await search_query(
                session, q.strip(), limit=SEARCH_LIMIT, category=category
            )
        except (AiUnavailableError, AiBudgetExceededError) as e:
            raise translate(e) from e
        window = hits[(page - 1) * per_page : page * per_page]
        return InnovationPage(
            items=[InnovationSummary.build(h.innovation, categories) for h in window],
            total=len(hits),
            page=page,
            per_page=per_page,
        )
    filters = [col(Innovation.status) == InnovationStatus.PUBLISHED]
    if category:
        filters.append(col(Innovation.category_slug) == category)
    total = (await session.exec(select(func.count()).where(*filters))).one()
    rows = (
        await session.exec(
            select(Innovation)
            .where(*filters)
            .order_by(func.lower(Innovation.title))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()
    return InnovationPage(
        items=[InnovationSummary.build(row, categories) for row in rows],
        total=int(total),
        page=page,
        per_page=per_page,
    )


@router.get("/innovations/{slug}", dependencies=[Depends(limiter)])
async def get_innovation(
    slug: Annotated[str, Path(max_length=200)], session: FromDishka[AsyncSession]
) -> InnovationDetail:
    innovation = (
        await session.exec(
            select(Innovation).where(
                col(Innovation.slug) == slug,
                col(Innovation.status) == InnovationStatus.PUBLISHED,
            )
        )
    ).first()
    if innovation is None:
        raise not_found(MISSING)
    return InnovationDetail.build_detail(innovation, await categories_by_slug(session))


@router.get("/categories", dependencies=[Depends(limiter)])
async def list_categories(session: FromDishka[AsyncSession]) -> list[CategoryOut]:
    counts = dict(
        (
            await session.exec(
                select(Innovation.category_slug, func.count())
                .where(col(Innovation.status) == InnovationStatus.PUBLISHED)
                .group_by(col(Innovation.category_slug))
            )
        ).all()
    )
    categories = sorted(
        (await categories_by_slug(session)).values(), key=lambda c: c.position
    )
    return [
        CategoryOut(
            slug=c.slug, name=c.name, icon_url=c.icon_url, count=counts.get(c.slug, 0)
        )
        for c in categories
    ]


@router.get("/powiats")
async def list_powiats() -> list[PowiatOut]:
    return [PowiatOut(slug=slug, name=name) for slug, name in POWIATS.items()]
