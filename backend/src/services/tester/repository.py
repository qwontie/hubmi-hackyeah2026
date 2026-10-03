import uuid
from collections.abc import Collection
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Executable, Result, delete, func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.modules import InnovationRef, Page, offset
from utils.db.models import Innovation, Need
from utils.db.models.feedback import VOTE_KINDS, Feedback, FeedbackKind
from utils.db.models.test_signup import SignupStatus, TesterRole, TestSignup

from .schemas import (
    AdminFeedback,
    AdminTestSignup,
    FeedbackSummary,
    InnovationFeedback,
    Votes,
)

SUMMARY_SQL = text("""
SELECT
    count(*) FILTER (WHERE kind = 'fits') AS fits,
    count(*) FILTER (WHERE kind = 'does_not_fit') AS does_not_fit,
    count(*) FILTER (WHERE kind = 'improvement') AS improvements,
    (
        SELECT count(*) FROM test_signup
        WHERE innovation_id = :id AND status <> 'rejected'
    ) AS testers
FROM feedback
WHERE innovation_id = :id
""")

BY_INNOVATION_SQL = """
WITH activity AS (
    SELECT innovation_id, kind::text AS kind, created_at FROM feedback
    UNION ALL
    SELECT innovation_id, 'tester' AS kind, created_at FROM test_signup
)
SELECT
    i.slug,
    i.title,
    count(*) FILTER (WHERE a.kind = 'fits') AS fits,
    count(*) FILTER (WHERE a.kind = 'does_not_fit') AS does_not_fit,
    count(*) FILTER (WHERE a.kind = 'improvement') AS improvements,
    count(*) FILTER (WHERE a.kind = 'tester') AS testers,
    max(a.created_at) AS last_at
FROM activity a
JOIN innovation i ON i.id = a.innovation_id
GROUP BY i.id, i.slug, i.title
ORDER BY {order}
LIMIT :limit OFFSET :offset
"""

ACTIVE_INNOVATIONS_SQL = text("""
SELECT count(*) FROM (
    SELECT innovation_id FROM feedback
    UNION
    SELECT innovation_id FROM test_signup
) active
""")

ORDERS = {
    "recent": "last_at DESC",
    "does_not_fit": "does_not_fit DESC, last_at DESC",
    "testers": "testers DESC, last_at DESC",
}


async def run(
    session: AsyncSession, statement: Executable, params: dict[str, Any] | None = None
) -> Result[Any]:
    connection = await session.connection()
    return await connection.execute(statement, params)


async def need_token_hash(session: AsyncSession, need_id: uuid.UUID) -> str | None:
    return (
        await session.exec(select(Need.edit_token_hash).where(Need.id == need_id))
    ).first()


async def summary(session: AsyncSession, innovation_id: uuid.UUID) -> FeedbackSummary:
    row = (await run(session, SUMMARY_SQL, {"id": innovation_id})).one()
    return FeedbackSummary(
        fits=row.fits,
        does_not_fit=row.does_not_fit,
        improvements=row.improvements,
        testers=row.testers,
    )


async def vote_counts(
    session: AsyncSession, innovation_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, Votes]:
    if not innovation_ids:
        return {}
    rows = await session.exec(
        select(
            Feedback.innovation_id,
            func.count().filter(col(Feedback.kind) == FeedbackKind.FITS),
            func.count().filter(col(Feedback.kind) == FeedbackKind.DOES_NOT_FIT),
        )
        .where(
            col(Feedback.innovation_id).in_(list(innovation_ids)),
            col(Feedback.kind).in_(VOTE_KINDS),
        )
        .group_by(col(Feedback.innovation_id))
    )
    return {innovation_id: Votes(up=up, down=down) for innovation_id, up, down in rows}


def votes_of(summary_: FeedbackSummary) -> Votes:
    return Votes(up=summary_.fits, down=summary_.does_not_fit)


async def _existing_vote(
    session: AsyncSession,
    *,
    innovation_id: uuid.UUID,
    voter_hash: str,
    need_id: uuid.UUID | None,
) -> Feedback | None:
    owners = [col(Feedback.voter_hash) == voter_hash]
    if need_id is not None:
        owners.append(col(Feedback.need_id) == need_id)
    rows = (
        await session.exec(
            select(Feedback).where(
                col(Feedback.innovation_id) == innovation_id,
                col(Feedback.kind).in_(VOTE_KINDS),
                or_(*owners),
            )
        )
    ).all()
    return next((r for r in rows if r.voter_hash == voter_hash), None) or next(
        iter(rows), None
    )


async def add_vote(  # noqa: PLR0913
    session: AsyncSession,
    *,
    innovation_id: uuid.UUID,
    kind: FeedbackKind,
    need_id: uuid.UUID | None,
    voter_hash: str,
    comment: str | None,
) -> Feedback:
    for attempt in range(2):
        feedback = await _existing_vote(
            session, innovation_id=innovation_id, voter_hash=voter_hash, need_id=need_id
        )
        if feedback is None:
            feedback = Feedback(
                innovation_id=innovation_id,
                kind=kind,
                need_id=need_id,
                voter_hash=voter_hash,
                comment=comment,
            )
        else:
            feedback.kind = kind
            feedback.comment = comment
            feedback.voter_hash = voter_hash
            feedback.updated_at = datetime.now(UTC)
        session.add(feedback)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            if attempt:
                raise
            continue
        await session.refresh(feedback)
        return feedback
    raise AssertionError


async def remove_vote(
    session: AsyncSession, *, innovation_id: uuid.UUID, voter_hash: str
) -> None:
    await run(
        session,
        delete(Feedback).where(
            col(Feedback.innovation_id) == innovation_id,
            col(Feedback.voter_hash) == voter_hash,
            col(Feedback.kind).in_(VOTE_KINDS),
        ),
    )
    await session.commit()


async def add_improvement(
    session: AsyncSession, *, innovation_id: uuid.UUID, text_: str
) -> Feedback:
    feedback = Feedback(
        innovation_id=innovation_id, kind=FeedbackKind.IMPROVEMENT, comment=text_
    )
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)
    return feedback


async def add_signup(  # noqa: PLR0913
    session: AsyncSession,
    *,
    innovation_id: uuid.UUID,
    who: TesterRole,
    organization: str | None,
    powiat: str | None,
    contact_email: str,
    note: str,
) -> TestSignup:
    signup = TestSignup(
        innovation_id=innovation_id,
        who=who,
        organization=organization,
        powiat=powiat,
        contact_email=contact_email,
        consent_at=datetime.now(UTC),
        note=note,
    )
    session.add(signup)
    await session.commit()
    await session.refresh(signup)
    return signup


def admin_feedback(feedback: Feedback, innovation: Innovation) -> AdminFeedback:
    return AdminFeedback(
        id=feedback.id,
        kind=feedback.kind,
        innovation=InnovationRef.of(innovation),
        need_id=feedback.need_id,
        comment=feedback.comment,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


def admin_signup(signup: TestSignup, innovation: Innovation) -> AdminTestSignup:
    return AdminTestSignup(
        id=signup.id,
        innovation=InnovationRef.of(innovation),
        who=signup.who,
        organization=signup.organization,
        powiat=signup.powiat,
        contact_email=signup.contact_email,
        note=signup.note,
        status=signup.status,
        created_at=signup.created_at,
    )


async def list_feedback(  # noqa: PLR0913
    session: AsyncSession,
    *,
    kind: FeedbackKind | None,
    innovation: str | None,
    q: str | None,
    page: int,
    per_page: int,
) -> Page[AdminFeedback]:
    filters: list[Any] = []
    if kind is not None:
        filters.append(Feedback.kind == kind)
    if innovation:
        filters.append(Innovation.slug == innovation)
    if q:
        filters.append(col(Feedback.comment).icontains(q, autoescape=True))
    base = select(Feedback, Innovation).join(
        Innovation, col(Innovation.id) == col(Feedback.innovation_id)
    )
    total = await session.scalar(
        select(func.count())
        .select_from(Feedback)
        .join(Innovation, col(Innovation.id) == col(Feedback.innovation_id))
        .where(*filters)
    )
    rows = await session.exec(
        base.where(*filters)
        .order_by(col(Feedback.updated_at).desc())
        .offset(offset(page, per_page))
        .limit(per_page)
    )
    return Page(
        items=[admin_feedback(feedback, inno) for feedback, inno in rows],
        total=total or 0,
        page=page,
        per_page=per_page,
    )


async def list_signups(  # noqa: PLR0913
    session: AsyncSession,
    *,
    who: TesterRole | None,
    status: SignupStatus | None,
    powiat: str | None,
    innovation: str | None,
    page: int,
    per_page: int,
) -> Page[AdminTestSignup]:
    filters: list[Any] = []
    if who is not None:
        filters.append(TestSignup.who == who)
    if status is not None:
        filters.append(TestSignup.status == status)
    if powiat:
        filters.append(TestSignup.powiat == powiat)
    if innovation:
        filters.append(Innovation.slug == innovation)
    total = await session.scalar(
        select(func.count())
        .select_from(TestSignup)
        .join(Innovation, col(Innovation.id) == col(TestSignup.innovation_id))
        .where(*filters)
    )
    rows = await session.exec(
        select(TestSignup, Innovation)
        .join(Innovation, col(Innovation.id) == col(TestSignup.innovation_id))
        .where(*filters)
        .order_by(col(TestSignup.created_at).desc())
        .offset(offset(page, per_page))
        .limit(per_page)
    )
    return Page(
        items=[admin_signup(signup, inno) for signup, inno in rows],
        total=total or 0,
        page=page,
        per_page=per_page,
    )


async def feedback_by_innovation(
    session: AsyncSession, *, sort: str, page: int, per_page: int
) -> Page[InnovationFeedback]:
    statement = text(BY_INNOVATION_SQL.format(order=ORDERS[sort]))
    rows = (
        await run(
            session, statement, {"limit": per_page, "offset": offset(page, per_page)}
        )
    ).all()
    return Page(
        items=[
            InnovationFeedback(
                innovation=InnovationRef(slug=row.slug, title=row.title),
                fits=row.fits,
                does_not_fit=row.does_not_fit,
                improvements=row.improvements,
                testers=row.testers,
                last_at=row.last_at,
            )
            for row in rows
        ],
        total=(await run(session, ACTIVE_INNOVATIONS_SQL)).scalar_one(),
        page=page,
        per_page=per_page,
    )
