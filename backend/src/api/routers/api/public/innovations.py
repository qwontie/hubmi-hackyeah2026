from typing import Annotated, Literal

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from services.ai import AiBudgetExceededError, AiUnavailableError
from services.library.images.service import stored_image
from services.needs import POWIATS
from services.search import search_query
from services.tester.repository import vote_counts
from utils.db.models.feedback import VOTE_KINDS, Feedback, FeedbackKind
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
image_limiter = rate_limit("innovation_image", per_minute=600)
SEARCH_LIMIT = 30
MISSING = "Nie znaleziono takiej innowacji."
IMAGE_MISSING = "Ta innowacja nie ma jeszcze obrazka."
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
SHORT_CACHE = "public, max-age=300"


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
        votes = await vote_counts(session, [h.innovation.id for h in window])
        return InnovationPage(
            items=[
                InnovationSummary.build(h.innovation, categories, votes) for h in window
            ],
            total=len(hits),
            page=page,
            per_page=per_page,
        )
    filters = [col(Innovation.status) == InnovationStatus.PUBLISHED]
    if category:
        filters.append(col(Innovation.category_slug) == category)
    total = (await session.exec(select(func.count()).where(*filters))).one()
    net = (
        select(
            col(Feedback.innovation_id).label("innovation_id"),
            (
                func.count().filter(col(Feedback.kind) == FeedbackKind.FITS)
                - func.count().filter(col(Feedback.kind) == FeedbackKind.DOES_NOT_FIT)
            ).label("net"),
        )
        .where(col(Feedback.kind).in_(VOTE_KINDS))
        .group_by(col(Feedback.innovation_id))
        .subquery()
    )
    rows = (
        await session.exec(
            select(Innovation)
            .outerjoin(net, net.c.innovation_id == Innovation.id)
            .where(*filters)
            .order_by(func.coalesce(net.c.net, 0).desc(), func.lower(Innovation.title))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()
    votes = await vote_counts(session, [row.id for row in rows])
    return InnovationPage(
        items=[InnovationSummary.build(row, categories, votes) for row in rows],
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
    return InnovationDetail.build_detail(
        innovation,
        await categories_by_slug(session),
        await vote_counts(session, [innovation.id]),
    )


@router.get(
    "/innovations/{slug}/image",
    response_class=Response,
    dependencies=[Depends(image_limiter)],
)
async def innovation_image(
    slug: Annotated[str, Path(max_length=200)],
    request: Request,
    session: FromDishka[AsyncSession],
    v: Annotated[int | None, Query(ge=1, le=100000)] = None,
    size: Annotated[Literal["full", "card"], Query()] = "full",
) -> Response:
    found = await stored_image(session, slug)
    if found is None or found[0].status != InnovationStatus.PUBLISHED:
        raise not_found(IMAGE_MISSING)
    image = found[1]
    etag = f'"{slug}-{image.version}-{size}"'
    headers = {
        "Cache-Control": IMMUTABLE_CACHE if v == image.version else SHORT_CACHE,
        "ETag": etag,
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    content = image.card if size == "card" else image.image
    return Response(content=content, media_type=image.mime_type, headers=headers)


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
