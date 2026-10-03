import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlmodel import col
from sqlmodel import select as entity_select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.sql import fetch
from utils.db.models import (
    ApplicationStatus,
    GrantApplication,
    GrantCall,
    GrantCallStatus,
)

from .schemas import (
    AdminGrantCall,
    ApplicationCounts,
    CallRef,
    GrantCallOut,
    GrantSection,
    Phase,
)


def now() -> datetime:
    return datetime.now(UTC)


def phase(call: GrantCall, at: datetime | None = None) -> Phase:
    moment = at or now()
    if moment < call.opens_at:
        return "upcoming"
    if moment < call.closes_at:
        return "open"
    return "closed"


def is_open(call: GrantCall) -> bool:
    return call.status == GrantCallStatus.PUBLISHED and phase(call) == "open"


def sections_of(call: GrantCall) -> list[GrantSection]:
    return [GrantSection.model_validate(raw) for raw in call.sections]


def public_out(call: GrantCall) -> GrantCallOut:
    return GrantCallOut(
        id=call.id,
        title=call.title,
        description=call.description,
        opens_at=call.opens_at,
        closes_at=call.closes_at,
        phase=phase(call),
        source_url=call.source_url,
        demo=call.demo,
        sections=sections_of(call),
        updated_at=call.updated_at,
    )


def ref(call: GrantCall) -> CallRef:
    return CallRef(
        id=call.id,
        title=call.title,
        opens_at=call.opens_at,
        closes_at=call.closes_at,
        phase=phase(call),
        demo=call.demo,
    )


async def counts(
    session: AsyncSession, call_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, ApplicationCounts]:
    ids = list(call_ids)
    found: dict[uuid.UUID, ApplicationCounts] = {i: ApplicationCounts() for i in ids}
    if not ids:
        return found
    rows = await fetch(
        session,
        select(
            col(GrantApplication.call_id), col(GrantApplication.status), func.count()
        )
        .where(col(GrantApplication.call_id).in_(ids))
        .group_by(col(GrantApplication.call_id), col(GrantApplication.status)),
    )
    for call_id, status, count in rows:
        bucket = found[call_id]
        bucket.total += count
        if status != ApplicationStatus.DRAFT:
            setattr(bucket, str(status), getattr(bucket, str(status)) + count)
    return found


def admin_view(call: GrantCall, applications: ApplicationCounts) -> AdminGrantCall:
    return AdminGrantCall(
        **public_out(call).model_dump(),
        status=call.status,
        template=call.template,
        applications=applications,
        created_at=call.created_at,
    )


async def admin_out(session: AsyncSession, call: GrantCall) -> AdminGrantCall:
    return admin_view(call, (await counts(session, [call.id]))[call.id])


async def list_public(
    session: AsyncSession, wanted: Phase | None
) -> list[GrantCallOut]:
    moment = now()
    query = entity_select(GrantCall).where(
        col(GrantCall.status) == GrantCallStatus.PUBLISHED,
        col(GrantCall.closes_at) > moment,
    )
    if wanted == "open":
        query = query.where(col(GrantCall.opens_at) <= moment)
    elif wanted == "upcoming":
        query = query.where(col(GrantCall.opens_at) > moment)
    rows = (await session.exec(query.order_by(col(GrantCall.opens_at)))).all()
    calls = sorted(rows, key=lambda c: (phase(c, moment) != "open", c.closes_at))
    return [public_out(call) for call in calls]


async def list_admin(
    session: AsyncSession, status: GrantCallStatus | None, page: int, per_page: int
) -> tuple[list[AdminGrantCall], int]:
    filters = [] if status is None else [col(GrantCall.status) == status]
    total = await session.scalar(
        select(func.count()).select_from(GrantCall).where(*filters)
    )
    rows = (
        await session.exec(
            entity_select(GrantCall)
            .where(*filters)
            .order_by(col(GrantCall.opens_at).desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()
    found = await counts(session, [call.id for call in rows])
    return [admin_view(call, found[call.id]) for call in rows], int(total or 0)


async def has_applications(session: AsyncSession, call_id: uuid.UUID) -> bool:
    found = await session.scalar(
        select(func.count())
        .select_from(GrantApplication)
        .where(col(GrantApplication.call_id) == call_id)
    )
    return bool(found)


async def due_for_open_notice(session: AsyncSession) -> list[GrantCall]:
    moment = now()
    rows = await session.exec(
        entity_select(GrantCall).where(
            col(GrantCall.status) == GrantCallStatus.PUBLISHED,
            col(GrantCall.demo).is_(False),
            col(GrantCall.opens_at) <= moment,
            col(GrantCall.closes_at) > moment,
            or_(col(GrantCall.notified_open_at).is_(None)),
        )
    )
    return list(rows.all())
