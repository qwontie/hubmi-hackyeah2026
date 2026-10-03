import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy import select as sa_select
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.modules import InnovationRef, Page, offset
from services.signing import signed_key
from utils.db.models import Innovation
from utils.db.models.demand import InnovationDemand

from .schemas import DemandByPowiat, DemandEntry
from .volunteers import powiat_label


def client_key(*, email: str | None, ip: str) -> str:
    if email:
        return signed_key("demand", "email", email.lower())
    return signed_key("demand", "ip", ip)


async def count(session: AsyncSession, innovation_id: uuid.UUID) -> int:
    total = await session.scalar(
        select(func.count())
        .select_from(InnovationDemand)
        .where(InnovationDemand.innovation_id == innovation_id)
    )
    return total or 0


async def add(
    session: AsyncSession,
    *,
    innovation_id: uuid.UUID,
    powiat: str,
    email: str | None,
    ip: str,
) -> InnovationDemand | None:
    now = datetime.now(UTC)
    statement = (
        insert(InnovationDemand)
        .values(
            id=uuid.uuid4(),
            innovation_id=innovation_id,
            powiat=powiat,
            contact_email=email,
            consent_at=now if email else None,
            client_key=client_key(email=email, ip=ip),
            day=now.date(),
        )
        .on_conflict_do_nothing(constraint="uq_innovation_demand_client_day")
        .returning(col(InnovationDemand.id))
    )
    connection = await session.connection()
    created = (await connection.execute(statement)).scalar_one_or_none()
    await session.commit()
    if created is None:
        return None
    return await session.get(InnovationDemand, created)


def entry(demand: InnovationDemand, innovation: Innovation) -> DemandEntry:
    return DemandEntry(
        id=demand.id,
        innovation=InnovationRef.of(innovation),
        powiat=demand.powiat,
        powiat_name=powiat_label(demand.powiat),
        email=demand.contact_email,
        created_at=demand.created_at,
    )


def _filters(innovation: str | None, powiat: str | None) -> list[Any]:
    filters: list[Any] = []
    if innovation:
        filters.append(Innovation.slug == innovation)
    if powiat:
        filters.append(InnovationDemand.powiat == powiat)
    return filters


async def by_powiat(
    session: AsyncSession,
    *,
    innovation: str | None,
    powiat: str | None,
    page: int,
    per_page: int,
) -> Page[DemandByPowiat]:
    filters = _filters(innovation, powiat)
    total_count = func.count().label("total")
    grouped = (
        sa_select(
            col(Innovation.slug),
            col(Innovation.title),
            col(InnovationDemand.powiat),
            total_count,
            func.count(col(InnovationDemand.contact_email)),
            func.max(col(InnovationDemand.created_at)),
        )
        .join(Innovation, col(Innovation.id) == col(InnovationDemand.innovation_id))
        .where(*filters)
        .group_by(
            col(Innovation.id),
            col(Innovation.slug),
            col(Innovation.title),
            col(InnovationDemand.powiat),
        )
    )
    total = await session.scalar(select(func.count()).select_from(grouped.subquery()))
    connection = await session.connection()
    rows = await connection.execute(
        grouped.order_by(
            total_count.desc(), func.max(col(InnovationDemand.created_at)).desc()
        )
        .offset(offset(page, per_page))
        .limit(per_page)
    )
    return Page(
        items=[
            DemandByPowiat(
                innovation=InnovationRef(slug=slug, title=title),
                powiat=powiat_slug,
                powiat_name=powiat_label(powiat_slug),
                count=hits,
                with_email=emails,
                last_at=last_at,
            )
            for slug, title, powiat_slug, hits, emails, last_at in rows
        ],
        total=total or 0,
        page=page,
        per_page=per_page,
    )


async def entries(  # noqa: PLR0913
    session: AsyncSession,
    *,
    innovation: str | None,
    powiat: str | None,
    with_email: bool | None,
    page: int,
    per_page: int,
) -> Page[DemandEntry]:
    filters = _filters(innovation, powiat)
    if with_email is True:
        filters.append(col(InnovationDemand.contact_email).is_not(None))
    elif with_email is False:
        filters.append(col(InnovationDemand.contact_email).is_(None))
    total = await session.scalar(
        select(func.count())
        .select_from(InnovationDemand)
        .join(Innovation, col(Innovation.id) == col(InnovationDemand.innovation_id))
        .where(*filters)
    )
    rows = await session.exec(
        select(InnovationDemand, Innovation)
        .join(Innovation, col(Innovation.id) == col(InnovationDemand.innovation_id))
        .where(*filters)
        .order_by(col(InnovationDemand.created_at).desc())
        .offset(offset(page, per_page))
        .limit(per_page)
    )
    return Page(
        items=[entry(demand, innovation_) for demand, innovation_ in rows],
        total=total or 0,
        page=page,
        per_page=per_page,
    )
