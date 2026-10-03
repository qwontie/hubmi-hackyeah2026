import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Executable, Result, func, text
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.modules import InnovationRef, Page, offset
from utils.db.models import Innovation, Need
from utils.db.models.feedback import Feedback, FeedbackKind
from utils.db.models.test_signup import SignupStatus, TesterRole, TestSignup

from .schemas import AdminFeedback, AdminTestSignup, FeedbackSummary, InnovationFeedback

SUMMARY_SQL = text("""
SELECT
    count(*) FILTER (WHERE kind = 'fits') AS fits,
    count(*) FILTER (WHERE kind = 'does_not_fit') AS does_not_fit,
    count(*) FILTER (WHERE kind = 'improvement') AS improvements,
    (SELECT count(*) FROM test_signup WHERE innovation_id = :id) AS testers
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


async def add_vote(
    session: AsyncSession,
    *,
    innovation_id: uuid.UUID,
    kind: FeedbackKind,
    need_id: uuid.UUID | None,
    comment: str | None,
) -> Feedback:
    if need_id is None:
        feedback = Feedback(innovation_id=innovation_id, kind=kind, comment=comment)
        session.add(feedback)
        await session.commit()
        await session.refresh(feedback)
        return feedback
    statement = (
        insert(Feedback)
        .values(
            id=uuid.uuid4(),
            innovation_id=innovation_id,
            kind=kind,
            need_id=need_id,
            comment=comment,
        )
        .on_conflict_do_update(
            index_elements=["need_id", "innovation_id"],
            index_where=text("need_id IS NOT NULL AND kind <> 'improvement'"),
            set_={"kind": kind, "comment": comment, "updated_at": func.now()},
        )
        .returning(col(Feedback.id))
    )
    feedback_id = (await run(session, statement)).scalar_one()
    await session.commit()
    feedback = await session.get(Feedback, feedback_id, populate_existing=True)
    assert feedback is not None
    return feedback


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


async def set_signup_status(
    session: AsyncSession, signup_id: uuid.UUID, status: SignupStatus
) -> AdminTestSignup | None:
    row = (
        await session.exec(
            select(TestSignup, Innovation)
            .join(Innovation, col(Innovation.id) == col(TestSignup.innovation_id))
            .where(TestSignup.id == signup_id)
        )
    ).first()
    if row is None:
        return None
    signup, innovation = row
    signup.status = status
    session.add(signup)
    await session.commit()
    await session.refresh(signup)
    return admin_signup(signup, innovation)


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
