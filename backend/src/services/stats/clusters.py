import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ColumnElement, func, select
from sqlmodel import col
from sqlmodel import select as entity_select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.needs import POWIATS
from services.sql import fetch, unaccent_like
from utils.db.models import Category, Need, NeedCluster, NeedStatus

from .queries import TIMEZONE

DAYS = 14
RECENT_DAYS = 7
TOP_POWIATS = 3


class PowiatCount(BaseModel):
    slug: str
    name: str
    count: int


class AdminCluster(BaseModel):
    id: uuid.UUID
    title: str
    summary: str
    category_slug: str | None
    category_name: str | None
    size: int
    waiting: int
    new_last_7d: int
    daily: list[int]
    powiats: list[PowiatCount]
    summary_stale: bool
    last_need_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ClusterPage(BaseModel):
    items: list[AdminCluster]
    total: int
    page: int
    per_page: int


class ClusterQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort: Literal["size", "recent", "growing"] = "size"
    category: str | None = Field(default=None, max_length=100)
    q: str | None = Field(default=None, max_length=200)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class MergeBody(BaseModel):
    into_id: uuid.UUID


class SplitBody(BaseModel):
    need_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class SplitResult(BaseModel):
    source: AdminCluster
    created: AdminCluster


def first_day() -> date:
    return datetime.now(ZoneInfo(TIMEZONE)).date() - timedelta(days=DAYS - 1)


def recent_count() -> Any:  # noqa: ANN401
    since = datetime.combine(
        first_day() + timedelta(days=DAYS - RECENT_DAYS),
        time.min,
        tzinfo=ZoneInfo(TIMEZONE),
    )
    return (
        select(func.count())
        .where(
            col(Need.cluster_id) == col(NeedCluster.id), col(Need.created_at) >= since
        )
        .scalar_subquery()
    )


def conditions(query: ClusterQuery) -> list[ColumnElement[bool]]:
    found: list[ColumnElement[bool]] = [col(NeedCluster.size) > 0]
    if query.category:
        found.append(col(NeedCluster.category_slug) == query.category)
    text = (query.q or "").strip()
    if text:
        found.append(unaccent_like(col(NeedCluster.title), text))
    return found


def ordering(sort: str) -> list[Any]:
    if sort == "recent":
        return [col(NeedCluster.last_need_at).desc().nulls_last()]
    if sort == "growing":
        return [recent_count().desc(), col(NeedCluster.size).desc()]
    return [col(NeedCluster.size).desc(), col(NeedCluster.last_need_at).desc()]


async def enrich(
    session: AsyncSession, clusters: list[NeedCluster]
) -> list[AdminCluster]:
    ids = [cluster.id for cluster in clusters]
    if not ids:
        return []
    start_day = first_day()
    start = datetime.combine(start_day, time.min, tzinfo=ZoneInfo(TIMEZONE))
    local_day = func.date(func.timezone(TIMEZONE, col(Need.created_at)))
    daily_rows = await fetch(
        session,
        select(col(Need.cluster_id), local_day.label("day"), func.count().label("n"))
        .where(col(Need.cluster_id).in_(ids), col(Need.created_at) >= start)
        .group_by(col(Need.cluster_id), local_day),
    )
    daily: dict[uuid.UUID, list[int]] = defaultdict(lambda: [0] * DAYS)
    for row in daily_rows:
        index = (row.day - start_day).days
        if 0 <= index < DAYS:
            daily[row.cluster_id][index] = row.n
    powiat_rows = await fetch(
        session,
        select(col(Need.cluster_id), col(Need.powiat), func.count().label("n"))
        .where(col(Need.cluster_id).in_(ids), col(Need.powiat).is_not(None))
        .group_by(col(Need.cluster_id), col(Need.powiat)),
    )
    powiats: dict[uuid.UUID, list[PowiatCount]] = defaultdict(list)
    for row in sorted(powiat_rows, key=lambda r: (-r.n, r.powiat)):
        if len(powiats[row.cluster_id]) < TOP_POWIATS:
            powiats[row.cluster_id].append(
                PowiatCount(
                    slug=row.powiat,
                    name=POWIATS.get(row.powiat, row.powiat),
                    count=row.n,
                )
            )
    waiting_rows = await fetch(
        session,
        select(col(Need.cluster_id), func.count().label("n"))
        .where(col(Need.cluster_id).in_(ids), col(Need.status) == NeedStatus.NEW)
        .group_by(col(Need.cluster_id)),
    )
    waiting = {row.cluster_id: row.n for row in waiting_rows}
    slugs = {cluster.category_slug for cluster in clusters if cluster.category_slug}
    names = {}
    if slugs:
        names = {
            row.slug: row.name
            for row in await fetch(
                session,
                select(col(Category.slug), col(Category.name)).where(
                    col(Category.slug).in_(slugs)
                ),
            )
        }
    return [
        AdminCluster(
            id=cluster.id,
            title=cluster.title,
            summary=cluster.summary,
            category_slug=cluster.category_slug,
            category_name=names.get(cluster.category_slug or ""),
            size=cluster.size,
            waiting=waiting.get(cluster.id, 0),
            new_last_7d=sum(daily[cluster.id][-RECENT_DAYS:]),
            daily=daily[cluster.id],
            powiats=powiats[cluster.id],
            summary_stale=cluster.summary_stale,
            last_need_at=cluster.last_need_at,
            created_at=cluster.created_at,
            updated_at=cluster.updated_at,
        )
        for cluster in clusters
    ]


async def list_clusters(
    session: AsyncSession, query: ClusterQuery
) -> tuple[list[AdminCluster], int]:
    where = conditions(query)
    total = await session.scalar(
        select(func.count()).select_from(NeedCluster).where(*where)
    )
    result = await session.exec(
        entity_select(NeedCluster)
        .where(*where)
        .order_by(*ordering(query.sort), col(NeedCluster.id))
        .offset((query.page - 1) * query.per_page)
        .limit(query.per_page)
    )
    return await enrich(session, list(result.all())), int(total or 0)


async def one(session: AsyncSession, cluster_id: uuid.UUID) -> AdminCluster | None:
    cluster = await session.get(NeedCluster, cluster_id)
    if cluster is None:
        return None
    return (await enrich(session, [cluster]))[0]
