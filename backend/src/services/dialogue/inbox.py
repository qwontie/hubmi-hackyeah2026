import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, and_, case, func, or_, select
from sqlmodel import col
from sqlmodel import select as entity_select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.sql import fetch, unaccent_like
from utils.db.models import (
    AdminUser,
    Category,
    Innovation,
    MatchResult,
    Message,
    MessageDirection,
    Need,
    NeedCluster,
    NeedStatus,
)

from .schemas import (
    AdminMessage,
    AdminNeed,
    AdminNeedDetail,
    AdminRef,
    CategoryRef,
    ClusterRef,
    ExpertRef,
    MatchDetail,
    MatchInnovation,
    MatchRef,
)

LIST_MATCHES = 3


@dataclass(frozen=True, slots=True)
class NeedFilters:
    status: NeedStatus | None = None
    cluster_id: uuid.UUID | None = None
    powiat: str | None = None
    category: str | None = None
    nothing_fits: bool | None = None
    unread: bool | None = None
    has_contact: bool | None = None
    q: str | None = None
    sort: str = "newest"


@dataclass(frozen=True, slots=True)
class Activity:
    unread: int
    count: int
    last_at: datetime | None


def unread_messages() -> Any:  # noqa: ANN401
    return (
        select(col(Message.need_id))
        .where(
            col(Message.direction) == MessageDirection.FROM_AUTHOR,
            col(Message.read_at).is_(None),
        )
        .scalar_subquery()
    )


def conditions(filters: NeedFilters) -> list[ColumnElement[bool]]:
    found: list[ColumnElement[bool]] = []
    if filters.status is not None:
        found.append(col(Need.status) == filters.status)
    if filters.cluster_id is not None:
        found.append(col(Need.cluster_id) == filters.cluster_id)
    if filters.powiat:
        found.append(col(Need.powiat) == filters.powiat)
    if filters.category:
        found.append(col(Need.category_slug) == filters.category)
    if filters.nothing_fits is not None:
        found.append(col(Need.nothing_fits).is_(filters.nothing_fits))
    if filters.has_contact is not None:
        contact = and_(
            col(Need.contact_email).is_not(None), col(Need.contact_consent).is_(True)
        )
        found.append(contact if filters.has_contact else ~contact)
    if filters.unread is not None:
        unread = col(Need.id).in_(unread_messages())
        found.append(unread if filters.unread else ~unread)
    if filters.q:
        query = filters.q.strip()
        options = [unaccent_like(Need.text, query), unaccent_like(Need.title, query)]
        if query.isdigit():
            options.append(col(Need.number) == int(query))
        found.append(or_(*options))
    return found


def ordering(sort: str) -> list[Any]:
    if sort == "oldest":
        return [col(Need.created_at).asc()]
    if sort == "activity":
        last = (
            select(func.max(col(Message.sent_at)))
            .where(col(Message.need_id) == col(Need.id))
            .scalar_subquery()
        )
        return [
            func.greatest(
                col(Need.created_at), func.coalesce(last, Need.created_at)
            ).desc()
        ]
    if sort == "waiting":
        return [
            case((col(Need.status) == NeedStatus.NEW, 0), else_=1),
            col(Need.created_at).asc(),
        ]
    return [col(Need.created_at).desc()]


async def clusters_of(
    session: AsyncSession, ids: set[uuid.UUID]
) -> dict[uuid.UUID, ClusterRef]:
    if not ids:
        return {}
    found = await fetch(
        session,
        select(
            col(NeedCluster.id), col(NeedCluster.title), col(NeedCluster.size)
        ).where(col(NeedCluster.id).in_(ids)),
    )
    return {
        row.id: ClusterRef(id=row.id, title=row.title, size=row.size) for row in found
    }


async def matches_of(
    session: AsyncSession, ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[MatchDetail]]:
    found: dict[uuid.UUID, list[MatchDetail]] = defaultdict(list)
    if not ids:
        return found
    rows = await fetch(
        session,
        select(
            col(MatchResult.need_id),
            col(MatchResult.rank),
            col(MatchResult.score),
            col(MatchResult.reason),
            col(Innovation.slug),
            col(Innovation.title),
            col(Innovation.lead),
            col(Category.slug).label("category_slug"),
            col(Category.name).label("category_name"),
        )
        .join(Innovation, col(Innovation.id) == col(MatchResult.innovation_id))
        .join(Category, col(Category.slug) == col(Innovation.category_slug))
        .where(col(MatchResult.need_id).in_(ids))
        .order_by(col(MatchResult.need_id), col(MatchResult.rank)),
    )
    for row in rows:
        found[row.need_id].append(
            MatchDetail(
                rank=row.rank,
                score=row.score,
                reason=row.reason,
                innovation=MatchInnovation(
                    slug=row.slug,
                    title=row.title,
                    lead=row.lead,
                    category=CategoryRef(
                        slug=row.category_slug, name=row.category_name
                    ),
                ),
            )
        )
    return found


async def activity_of(
    session: AsyncSession, ids: list[uuid.UUID]
) -> dict[uuid.UUID, Activity]:
    if not ids:
        return {}
    unread = and_(
        col(Message.direction) == MessageDirection.FROM_AUTHOR,
        col(Message.read_at).is_(None),
    )
    rows = await fetch(
        session,
        select(
            col(Message.need_id),
            func.count().filter(unread).label("unread"),
            func.count().label("total"),
            func.max(col(Message.sent_at)).label("last_at"),
        )
        .where(col(Message.need_id).in_(ids))
        .group_by(col(Message.need_id)),
    )
    return {
        row.need_id: Activity(unread=row.unread, count=row.total, last_at=row.last_at)
        for row in rows
    }


def admin_need(
    need: Need,
    cluster: ClusterRef | None,
    matches: list[MatchDetail],
    activity: Activity | None,
) -> AdminNeed:
    return AdminNeed(
        id=need.id,
        number=need.number,
        text=need.text,
        title=need.title,
        origin=need.origin,
        powiat=need.powiat,
        category_slug=need.category_slug,
        contact_email=need.contact_email if need.contact_consent else None,
        has_contact=bool(need.contact_email and need.contact_consent),
        status=need.status,
        nothing_fits=need.nothing_fits,
        cluster=cluster,
        matches=[
            MatchRef(
                slug=match.innovation.slug,
                title=match.innovation.title,
                score=match.score,
            )
            for match in matches[:LIST_MATCHES]
        ],
        unread=activity.unread if activity else 0,
        messages_count=activity.count if activity else 0,
        last_message_at=activity.last_at if activity else None,
        created_at=need.created_at,
        updated_at=need.updated_at,
    )


async def build(session: AsyncSession, needs: list[Need]) -> list[AdminNeed]:
    ids = [need.id for need in needs]
    clusters = await clusters_of(
        session, {need.cluster_id for need in needs if need.cluster_id}
    )
    matches = await matches_of(session, ids)
    activity = await activity_of(session, ids)
    return [
        admin_need(
            need,
            clusters.get(need.cluster_id) if need.cluster_id else None,
            matches.get(need.id, []),
            activity.get(need.id),
        )
        for need in needs
    ]


async def list_needs(
    session: AsyncSession, filters: NeedFilters, page: int, per_page: int
) -> tuple[list[AdminNeed], int]:
    where = conditions(filters)
    total = await session.scalar(select(func.count()).select_from(Need).where(*where))
    result = await session.exec(
        entity_select(Need)
        .where(*where)
        .order_by(*ordering(filters.sort), col(Need.id))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    needs = list(result.all())
    return await build(session, needs), int(total or 0)


async def get_need(session: AsyncSession, need_id: uuid.UUID) -> Need | None:
    return await session.get(Need, need_id)


async def admin_messages(
    session: AsyncSession, owned: ColumnElement[bool]
) -> list[AdminMessage]:
    result = await session.exec(
        entity_select(Message, col(AdminUser.login))
        .outerjoin(AdminUser, col(AdminUser.id) == col(Message.admin_id))
        .where(owned)
        .order_by(col(Message.sent_at), col(Message.created_at))
    )
    return [admin_message(message, login) for message, login in result.all()]


def admin_message(message: Message, login: str | None) -> AdminMessage:
    return AdminMessage(
        id=message.id,
        need_id=message.need_id,
        idea_id=message.idea_id,
        direction=message.direction,
        body=message.body,
        sent_at=message.sent_at,
        delivery_status=message.delivery_status,
        admin=AdminRef(id=message.admin_id, login=login)
        if message.admin_id and login
        else None,
        read_at=message.read_at,
        expert=expert_ref(message),
    )


def expert_ref(message: Message) -> ExpertRef | None:
    if not message.expert_name:
        return None
    return ExpertRef(display_name=message.expert_name, expertise=message.expert_field)


async def need_detail(session: AsyncSession, need: Need) -> AdminNeedDetail:
    summary = (await build(session, [need]))[0]
    matches = await matches_of(session, [need.id])
    return AdminNeedDetail(
        **summary.model_dump(),
        match_details=matches.get(need.id, []),
        messages=await admin_messages(session, col(Message.need_id) == need.id),
        can_email=bool(need.contact_email and need.contact_consent),
    )
