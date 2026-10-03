import hashlib
from dataclasses import dataclass, field
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
from utils.db.models.need import Need, NeedCluster, NeedStatus
from utils.db.models.powiat_figure import PowiatFigure

from .powiat_tables import REGION, clean_title, parse_tables

GEOJSON_PATH = Path(__file__).parent / "data" / "malopolska-powiaty.geojson"
TOP_CLUSTERS = 3
PROBLEM_MIN_NEEDS = 3
ANSWERED = (NeedStatus.ANSWERED, NeedStatus.CLOSED)
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


class Problem(BaseModel):
    title: str
    open: int
    answered: int


class PublicPowiat(BaseModel):
    slug: str
    name: str
    figures: list[PowiatFigureOut]
    needs_open: int
    needs_answered: int
    problems: list[Problem]
    other_open: int
    other_answered: int


class PublicMap(BaseModel):
    powiats: list[PublicPowiat]
    indicators: list[Indicator]
    needs_open: int
    needs_answered: int
    needs_without_powiat: int
    problem_min_needs: int
    geojson_url: str


class ClusterInPowiat(BaseModel):
    id: str
    title: str
    count: int


class AdminPowiat(PublicPowiat):
    needs_count: int
    needs_recent: int
    top_clusters: list[ClusterInPowiat]


class AdminMap(PublicMap):
    powiats: list[AdminPowiat]
    needs_total: int
    recent_days: int


@dataclass(slots=True)
class PowiatNeeds:
    open: int = 0
    answered: int = 0
    problems: list[Problem] = field(default_factory=list)
    other_open: int = 0
    other_answered: int = 0


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


async def _needs_by_powiat(
    session: AsyncSession,
) -> tuple[dict[str | None, PowiatNeeds], int, int]:
    rows = (
        await session.exec(
            select(
                col(Need.powiat),
                col(NeedCluster.title),
                func.count().filter(col(Need.status) == NeedStatus.NEW),
                func.count().filter(col(Need.status).in_(ANSWERED)),
            )
            .outerjoin(NeedCluster, col(NeedCluster.id) == col(Need.cluster_id))
            .group_by(col(Need.powiat), col(NeedCluster.id), col(NeedCluster.title))
        )
    ).all()
    stats: dict[str | None, PowiatNeeds] = {}
    open_total = answered_total = 0
    for powiat, title, open_count, answered_count in rows:
        entry = stats.setdefault(powiat, PowiatNeeds())
        entry.open += open_count
        entry.answered += answered_count
        open_total += open_count
        answered_total += answered_count
        if title and open_count + answered_count >= PROBLEM_MIN_NEEDS:
            entry.problems.append(
                Problem(title=title, open=open_count, answered=answered_count)
            )
        else:
            entry.other_open += open_count
            entry.other_answered += answered_count
    for entry in stats.values():
        entry.problems.sort(key=lambda p: (-(p.open + p.answered), p.title))
    return stats, open_total, answered_total


async def public_map(session: AsyncSession) -> PublicMap:
    figures = await _latest_figures(session)
    by_powiat: dict[str, list[PowiatFigureOut]] = {}
    for figure in figures:
        if figure.powiat != REGION:
            by_powiat.setdefault(figure.powiat, []).append(_figure_out(figure))
    for items in by_powiat.values():
        items.sort(key=attrgetter("key"))
    needs, open_total, answered_total = await _needs_by_powiat(session)
    powiats: list[PublicPowiat] = []
    for slug, name in POWIATS.items():
        entry = needs.get(slug, PowiatNeeds())
        powiats.append(
            PublicPowiat(
                slug=slug,
                name=name,
                figures=by_powiat.get(slug, []),
                needs_open=entry.open,
                needs_answered=entry.answered,
                problems=entry.problems,
                other_open=entry.other_open,
                other_answered=entry.other_answered,
            )
        )
    without = needs.get(None, PowiatNeeds())
    return PublicMap(
        powiats=powiats,
        indicators=_indicators(figures),
        needs_open=open_total,
        needs_answered=answered_total,
        needs_without_powiat=without.open + without.answered,
        problem_min_needs=PROBLEM_MIN_NEEDS,
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
        needs_open=base.needs_open,
        needs_answered=base.needs_answered,
        needs_without_powiat=base.needs_without_powiat,
        problem_min_needs=base.problem_min_needs,
        needs_total=needs_total,
        recent_days=recent_days,
        geojson_url=GEOJSON_URL,
    )
