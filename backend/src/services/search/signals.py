import uuid
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import Subquery, func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models.feedback import VOTE_KINDS, Feedback, FeedbackKind
from utils.db.models.innovation import Innovation
from utils.db.models.test_signup import TestSignup
from utils.db.models.volunteer import Recommendation, VolunteerReport

CHECKED_RECOMMENDATIONS = (Recommendation.YES, Recommendation.AFTER_CHANGES)


@dataclass(frozen=True, slots=True)
class Signals:
    up: int = 0
    down: int = 0
    reports: int = 0

    @property
    def checked(self) -> bool:
        return self.reports > 0


NO_SIGNALS = Signals()


def votes_by_innovation(ids: Collection[uuid.UUID] | None = None) -> Subquery:
    filters = [col(Feedback.kind).in_(VOTE_KINDS)]
    if ids is not None:
        filters.append(col(Feedback.innovation_id).in_(list(ids)))
    return (
        select(
            col(Feedback.innovation_id).label("innovation_id"),
            func.count().filter(col(Feedback.kind) == FeedbackKind.FITS).label("up"),
            func.count()
            .filter(col(Feedback.kind) == FeedbackKind.DOES_NOT_FIT)
            .label("down"),
        )
        .where(*filters)
        .group_by(col(Feedback.innovation_id))
        .subquery()
    )


def reports_by_innovation(ids: Collection[uuid.UUID] | None = None) -> Subquery:
    filters = [col(VolunteerReport.recommend).in_(CHECKED_RECOMMENDATIONS)]
    if ids is not None:
        filters.append(col(TestSignup.innovation_id).in_(list(ids)))
    return (
        select(
            col(TestSignup.innovation_id).label("innovation_id"),
            func.count().label("reports"),
        )
        .join(VolunteerReport, col(VolunteerReport.signup_id) == col(TestSignup.id))
        .where(*filters)
        .group_by(col(TestSignup.innovation_id))
        .subquery()
    )


async def innovation_signals(
    session: AsyncSession, ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, Signals]:
    if not ids:
        return {}
    votes = votes_by_innovation(ids)
    reports = reports_by_innovation(ids)
    rows = await session.exec(
        select(
            Innovation.id,
            func.coalesce(votes.c.up, 0),
            func.coalesce(votes.c.down, 0),
            func.coalesce(reports.c.reports, 0),
        )
        .outerjoin(votes, votes.c.innovation_id == Innovation.id)
        .outerjoin(reports, reports.c.innovation_id == Innovation.id)
        .where(col(Innovation.id).in_(list(ids)))
    )
    return {
        innovation_id: Signals(up=up, down=down, reports=count)
        for innovation_id, up, down, count in rows
    }


def badge_order[T](
    items: Sequence[T],
    signals: Mapping[uuid.UUID, Signals],
    key: Callable[[T], uuid.UUID],
) -> list[T]:
    def rank(item: T) -> tuple[bool, int]:
        found = signals.get(key(item), NO_SIGNALS)
        return not found.checked, -found.up

    return sorted(items, key=rank)
