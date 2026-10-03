import hashlib
from datetime import UTC, datetime, timedelta
from functools import cache
from operator import attrgetter
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.needs import POWIATS
from utils.db.models.material import KnowledgeStatus, Material
from utils.db.models.material_text import MaterialText
from utils.db.models.need import Need, NeedCluster
from utils.db.models.powiat_figure import PowiatFigure

from .powiat_tables import REGION, clean_title, parse_tables

GEOJSON_PATH = Path(__file__).parent / "data" / "malopolska-powiaty.geojson"
TOP_CLUSTERS = 3
RECENT_DAYS = 30


class PowiatFigureOut(BaseModel):
    key: str
    label: str
    value: float
    unit: str
    year: int
    source_title: str
    source_url: str
    page: int | None


class Indicator(BaseModel):
    key: str
    label: str
    unit: str
    year: int
    min: float
    max: float
    regional: float | None
    source_title: str
    source_url: str
    page: int | None


class PublicPowiat(BaseModel):
    slug: str
    name: str
    figures: list[PowiatFigureOut]


class PublicMap(BaseModel):
    powiats: list[PublicPowiat]
    indicators: list[Indicator]
    geojson_url: str


class ClusterInPowiat(BaseModel):
    id: str
    title: str
    count: int


class AdminPowiat(PublicPowiat):
    needs_count: int
    needs_recent: int
    top_clusters: list[ClusterInPowiat]


class AdminMap(BaseModel):
    powiats: list[AdminPowiat]
    indicators: list[Indicator]
    needs_total: int
    needs_without_powiat: int
    recent_days: int
    geojson_url: str


GEOJSON_URL = "/api/map/powiats.geojson"


@cache
def geojson_bytes() -> bytes:
    return GEOJSON_PATH.read_bytes()


@cache
def geojson_etag() -> str:
    return hashlib.sha256(geojson_bytes()).hexdigest()[:16]


async def refresh_powiat_figures(session: AsyncSession) -> int:
    rows = (
        await session.exec(
            select(Material, MaterialText)
            .join(MaterialText, col(MaterialText.material_id) == col(Material.id))
            .where(Material.status == KnowledgeStatus.PUBLISHED)
        )
    ).all()
    existing = {
        (f.powiat, f.key, f.year): f
        for f in (await session.exec(select(PowiatFigure))).all()
    }
    written = 0
    for material, text in rows:
        for table in parse_tables(list(text.pages)):
            year = table.year or material.year
            if year is None:
                continue
            for value in table.values:
                figure = existing.get((value.powiat, table.key, year)) or PowiatFigure(
                    powiat=value.powiat,
                    key=table.key,
                    year=year,
                    label="",
                    value=value.value,
                    source_url=material.file_url,
                )
                figure.label = clean_title(table.title)
                figure.value = value.value
                figure.unit = table.unit
                figure.source_url = material.file_url
                figure.source_title = material.title
                figure.page = table.page
                existing[(value.powiat, table.key, year)] = figure
                session.add(figure)
                written += 1
    await session.commit()
    return written


def _figure_out(figure: PowiatFigure) -> PowiatFigureOut:
    return PowiatFigureOut(
        key=figure.key,
        label=figure.label,
        value=figure.value,
        unit=figure.unit,
        year=figure.year,
        source_title=figure.source_title,
        source_url=figure.source_url,
        page=figure.page,
    )


async def _latest_figures(session: AsyncSession) -> list[PowiatFigure]:
    rows = list((await session.exec(select(PowiatFigure))).all())
    latest: dict[str, int] = {}
    for row in rows:
        latest[row.key] = max(latest.get(row.key, row.year), row.year)
    return [
        r
        for r in rows
        if r.year == latest[r.key] and (r.powiat in POWIATS or r.powiat == REGION)
    ]


def _indicators(figures: list[PowiatFigure]) -> list[Indicator]:
    grouped: dict[str, list[PowiatFigure]] = {}
    regional: dict[str, float] = {}
    for figure in figures:
        if figure.powiat == REGION:
            regional[figure.key] = figure.value
        else:
            grouped.setdefault(figure.key, []).append(figure)
    indicators: list[Indicator] = []
    for key, items in sorted(grouped.items()):
        first = items[0]
        values = [i.value for i in items]
        indicators.append(
            Indicator(
                key=key,
                label=first.label,
                unit=first.unit,
                year=first.year,
                min=min(values),
                max=max(values),
                regional=regional.get(key),
                source_title=first.source_title,
                source_url=first.source_url,
                page=first.page,
            )
        )
    return indicators


async def public_map(session: AsyncSession) -> PublicMap:
    figures = await _latest_figures(session)
    by_powiat: dict[str, list[PowiatFigureOut]] = {}
    for figure in figures:
        if figure.powiat != REGION:
            by_powiat.setdefault(figure.powiat, []).append(_figure_out(figure))
    for items in by_powiat.values():
        items.sort(key=attrgetter("key"))
    return PublicMap(
        powiats=[
            PublicPowiat(slug=slug, name=name, figures=by_powiat.get(slug, []))
            for slug, name in POWIATS.items()
        ],
        indicators=_indicators(figures),
        geojson_url=GEOJSON_URL,
    )


async def admin_map(
    session: AsyncSession, *, recent_days: int = RECENT_DAYS
) -> AdminMap:
    base = await public_map(session)
    since = datetime.now(UTC) - timedelta(days=recent_days)
    counts: dict[str | None, tuple[int, int]] = {
        powiat: (int(total), int(recent or 0))
        for powiat, total, recent in (
            await session.exec(
                select(
                    col(Need.powiat),
                    func.count(),
                    func.count().filter(col(Need.created_at) >= since),
                ).group_by(col(Need.powiat))
            )
        ).all()
    }
    cluster_rows = (
        await session.exec(
            select(
                col(Need.powiat),
                col(NeedCluster.id),
                col(NeedCluster.title),
                func.count().label("n"),
            )
            .join(NeedCluster, col(NeedCluster.id) == col(Need.cluster_id))
            .where(col(Need.powiat).is_not(None))
            .group_by(col(Need.powiat), col(NeedCluster.id), col(NeedCluster.title))
            .order_by(col(Need.powiat), func.count().desc())
        )
    ).all()
    clusters: dict[str, list[ClusterInPowiat]] = {}
    for powiat, cluster_id, title, count in cluster_rows:
        bucket = clusters.setdefault(str(powiat), [])
        if len(bucket) < TOP_CLUSTERS:
            bucket.append(ClusterInPowiat(id=str(cluster_id), title=title, count=count))
    needs_total = sum(total for total, _ in counts.values())
    return AdminMap(
        powiats=[
            AdminPowiat(
                **powiat.model_dump(),
                needs_count=counts.get(powiat.slug, (0, 0))[0],
                needs_recent=counts.get(powiat.slug, (0, 0))[1],
                top_clusters=clusters.get(powiat.slug, []),
            )
            for powiat in base.powiats
        ],
        indicators=base.indicators,
        needs_total=needs_total,
        needs_without_powiat=counts.get(None, (0, 0))[0],
        recent_days=recent_days,
        geojson_url=GEOJSON_URL,
    )
