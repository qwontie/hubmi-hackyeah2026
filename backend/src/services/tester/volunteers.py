import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import func, or_
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import Select

from services.dialogue.audit import record
from services.mail import Email, Mailer
from services.modules import InnovationRef, Page, offset
from services.needs import POWIATS
from services.signing import key_matches, signed_key
from utils.db.models import AdminUser, Innovation
from utils.db.models.adaptation import Adaptation
from utils.db.models.message import MessageDelivery
from utils.db.models.test_signup import SignupStatus, TesterRole, TestSignup
from utils.db.models.volunteer import (
    Recommendation,
    VolunteerMessage,
    VolunteerMessageKind,
    VolunteerReport,
)
from utils.env import env

from . import emails
from .schemas import (
    AdaptationVolunteers,
    AdminVolunteer,
    AdminVolunteerDetail,
    InnovationReports,
    RecommendCounts,
    VolunteerCounts,
    VolunteerDrafts,
    VolunteerMessageOut,
    VolunteerReportOut,
    VolunteerView,
)

REPORT_LINK = "volunteer-report"
DELIVERY_ERROR_LIMIT = 500
OPEN = frozenset({SignupStatus.NEW, SignupStatus.ACCEPTED, SignupStatus.REPORTED})
EDITABLE = frozenset({SignupStatus.ACCEPTED, SignupStatus.REPORTED})
NEAR_ADAPTATION = (SignupStatus.NEW, SignupStatus.ACCEPTED, SignupStatus.REPORTED)


class Action(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    CLOSE = "close"
    REPORT = "report"


TRANSITIONS: dict[Action, tuple[frozenset[SignupStatus], SignupStatus]] = {
    Action.ACCEPT: (frozenset({SignupStatus.NEW}), SignupStatus.ACCEPTED),
    Action.REJECT: (frozenset({SignupStatus.NEW}), SignupStatus.REJECTED),
    Action.CLOSE: (EDITABLE, SignupStatus.CLOSED),
    Action.REPORT: (EDITABLE, SignupStatus.REPORTED),
}


class InvalidTransitionError(ValueError):
    def __init__(self, current: SignupStatus, action: Action) -> None:
        super().__init__(f"{action.value} is not allowed from {current.value}")
        self.current = current
        self.action = action


def next_status(current: SignupStatus, action: Action) -> SignupStatus:
    allowed, target = TRANSITIONS[action]
    if current not in allowed:
        raise InvalidTransitionError(current, action)
    return target


def report_token(signup_id: uuid.UUID) -> str:
    return signed_key(REPORT_LINK, signup_id)


def token_opens(signup_id: uuid.UUID, token: str | None) -> bool:
    return key_matches(token, REPORT_LINK, signup_id)


def report_url(signup_id: uuid.UUID) -> str:
    base = env.mailer.public_url.rstrip("/")
    return f"{base}/wolontariat/{signup_id}#token={report_token(signup_id)}"


def powiat_label(slug: str | None) -> str | None:
    return POWIATS.get(slug) if slug else None


def report_out(report: VolunteerReport | None) -> VolunteerReportOut | None:
    if report is None:
        return None
    return VolunteerReportOut(
        activity=report.activity,
        participants=report.participants,
        worked=report.worked,
        not_worked=report.not_worked,
        recommend=report.recommend,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def admin_volunteer(
    signup: TestSignup, innovation: Innovation, report: VolunteerReport | None
) -> AdminVolunteer:
    return AdminVolunteer(
        id=signup.id,
        innovation=InnovationRef.of(innovation),
        who=signup.who,
        organization=signup.organization,
        powiat=signup.powiat,
        powiat_name=powiat_label(signup.powiat),
        email=signup.contact_email,
        proposal=signup.note,
        status=signup.status,
        decision_reason=signup.decision_reason,
        decided_at=signup.decided_at,
        report=report_out(report),
        created_at=signup.created_at,
        updated_at=signup.updated_at,
    )


def volunteer_view(
    signup: TestSignup, innovation: Innovation, report: VolunteerReport | None
) -> VolunteerView:
    return VolunteerView(
        id=signup.id,
        innovation=InnovationRef.of(innovation),
        powiat=signup.powiat,
        powiat_name=powiat_label(signup.powiat),
        proposal=signup.note,
        status=signup.status,
        editable=signup.status in EDITABLE,
        report=report_out(report),
    )


def joined() -> Select[tuple[TestSignup, Innovation, VolunteerReport]]:
    return (
        select(TestSignup, Innovation, VolunteerReport)
        .join(Innovation, col(Innovation.id) == col(TestSignup.innovation_id))
        .outerjoin(
            VolunteerReport, col(VolunteerReport.signup_id) == col(TestSignup.id)
        )
    )


async def load(
    session: AsyncSession, signup_id: uuid.UUID
) -> tuple[TestSignup, Innovation, VolunteerReport | None] | None:
    row = (await session.exec(joined().where(TestSignup.id == signup_id))).first()
    return None if row is None else (row[0], row[1], row[2])


async def open_application(
    session: AsyncSession, *, innovation_id: uuid.UUID, email: str
) -> TestSignup | None:
    return (
        await session.exec(
            select(TestSignup).where(
                TestSignup.innovation_id == innovation_id,
                func.lower(col(TestSignup.contact_email)) == email.lower(),
                col(TestSignup.status).in_(OPEN),
            )
        )
    ).first()


async def apply(  # noqa: PLR0913
    session: AsyncSession,
    *,
    innovation_id: uuid.UUID,
    who: TesterRole,
    organization: str | None,
    powiat: str,
    email: str,
    proposal: str,
) -> tuple[TestSignup, bool]:
    existing = await open_application(session, innovation_id=innovation_id, email=email)
    if existing is not None:
        return existing, True
    signup = TestSignup(
        innovation_id=innovation_id,
        who=who,
        organization=organization,
        powiat=powiat,
        contact_email=email,
        consent_at=datetime.now(UTC),
        note=proposal,
    )
    session.add(signup)
    await session.commit()
    await session.refresh(signup)
    return signup, False


async def save_report(  # noqa: PLR0913
    session: AsyncSession,
    signup: TestSignup,
    *,
    activity: str,
    participants: int,
    worked: str,
    not_worked: str,
    recommend: Recommendation,
) -> tuple[VolunteerReport, bool]:
    signup.status = next_status(signup.status, Action.REPORT)
    report = (
        await session.exec(
            select(VolunteerReport).where(VolunteerReport.signup_id == signup.id)
        )
    ).first()
    now = datetime.now(UTC)
    first = report is None
    if report is None:
        report = VolunteerReport(
            signup_id=signup.id,
            activity=activity,
            participants=participants,
            worked=worked,
            not_worked=not_worked,
            recommend=recommend,
            created_at=now,
        )
    else:
        report.activity = activity
        report.participants = participants
        report.worked = worked
        report.not_worked = not_worked
        report.recommend = recommend
    report.updated_at = now
    signup.updated_at = now
    session.add(signup)
    session.add(report)
    await session.commit()
    await session.refresh(report)
    await session.refresh(signup)
    return report, first


def drafts(innovation: Innovation) -> VolunteerDrafts:
    return VolunteerDrafts(
        accept=emails.accept_draft(innovation.title),
        reject=emails.reject_draft(innovation.title),
    )


def message_out(message: VolunteerMessage, login: str | None) -> VolunteerMessageOut:
    return VolunteerMessageOut(
        id=message.id,
        kind=message.kind,
        body=message.body,
        admin=login,
        delivery_status=message.delivery_status,
        delivery_error=message.delivery_error,
        created_at=message.created_at,
    )


async def messages_of(
    session: AsyncSession, signup_id: uuid.UUID
) -> list[VolunteerMessageOut]:
    rows = await session.exec(
        select(VolunteerMessage, AdminUser.login)
        .outerjoin(AdminUser, col(AdminUser.id) == col(VolunteerMessage.admin_id))
        .where(VolunteerMessage.signup_id == signup_id)
        .order_by(col(VolunteerMessage.created_at))
    )
    return [message_out(message, login) for message, login in rows]


async def detail(
    session: AsyncSession, signup_id: uuid.UUID
) -> AdminVolunteerDetail | None:
    row = await load(session, signup_id)
    if row is None:
        return None
    signup, innovation, report = row
    base = admin_volunteer(signup, innovation, report)
    return AdminVolunteerDetail(
        **base.model_dump(),
        messages=await messages_of(session, signup_id),
        drafts=drafts(innovation),
    )


def email_for(signup: TestSignup, message: VolunteerMessage, link: str | None) -> Email:
    key = f"volunteer-message-{message.id}"
    if message.kind == VolunteerMessageKind.ACCEPT:
        return emails.accepted(
            to=signup.contact_email, body=message.body, link=str(link), key=key
        )
    if message.kind == VolunteerMessageKind.REJECT:
        return emails.rejected(to=signup.contact_email, body=message.body, key=key)
    return emails.message(
        to=signup.contact_email, body=message.body, link=link, key=key
    )


async def send(  # noqa: PLR0913
    session: AsyncSession,
    *,
    signup: TestSignup,
    kind: VolunteerMessageKind,
    body: str,
    admin: AdminUser,
    mailer: Mailer,
) -> VolunteerMessage:
    message = VolunteerMessage(
        signup_id=signup.id,
        kind=kind,
        body=body,
        admin_id=admin.id,
        delivery_status=MessageDelivery.PENDING,
    )
    session.add(message)
    session.add(signup)
    record(
        session,
        admin,
        f"volunteer.{kind.value}",
        target=("test_signup", signup.id),
        details={"status": signup.status.value},
    )
    await session.commit()
    await session.refresh(message)
    await session.refresh(signup)
    link = report_url(signup.id) if signup.status in EDITABLE else None
    delivery = await mailer.send(email_for(signup, message, link))
    message.delivery_status = MessageDelivery(delivery.status.value)
    message.provider_id = delivery.provider_id
    message.delivery_error = (
        delivery.error[:DELIVERY_ERROR_LIMIT] if delivery.error else None
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def decide(  # noqa: PLR0913
    session: AsyncSession,
    signup: TestSignup,
    *,
    action: Action,
    body: str,
    reason: str | None,
    admin: AdminUser,
    mailer: Mailer,
) -> VolunteerMessage:
    signup.status = next_status(signup.status, action)
    signup.decided_at = datetime.now(UTC)
    signup.decision_reason = reason
    kind = (
        VolunteerMessageKind.ACCEPT
        if action == Action.ACCEPT
        else VolunteerMessageKind.REJECT
    )
    return await send(
        session, signup=signup, kind=kind, body=body, admin=admin, mailer=mailer
    )


async def close(session: AsyncSession, signup: TestSignup, admin: AdminUser) -> None:
    signup.status = next_status(signup.status, Action.CLOSE)
    session.add(signup)
    record(session, admin, "volunteer.close", target=("test_signup", signup.id))
    await session.commit()


def _filters(
    *,
    status: SignupStatus | None,
    who: TesterRole | None,
    powiat: str | None,
    innovation: str | None,
    q: str | None,
) -> list[Any]:
    filters: list[Any] = []
    if status is not None:
        filters.append(TestSignup.status == status)
    if who is not None:
        filters.append(TestSignup.who == who)
    if powiat:
        filters.append(TestSignup.powiat == powiat)
    if innovation:
        filters.append(Innovation.slug == innovation)
    if q:
        filters.append(
            or_(
                col(TestSignup.note).icontains(q, autoescape=True),
                col(TestSignup.contact_email).icontains(q, autoescape=True),
            )
        )
    return filters


async def list_volunteers(  # noqa: PLR0913
    session: AsyncSession,
    *,
    status: SignupStatus | None,
    who: TesterRole | None,
    powiat: str | None,
    innovation: str | None,
    q: str | None,
    page: int,
    per_page: int,
) -> Page[AdminVolunteer]:
    filters = _filters(
        status=status, who=who, powiat=powiat, innovation=innovation, q=q
    )
    total = await session.scalar(
        select(func.count())
        .select_from(TestSignup)
        .join(Innovation, col(Innovation.id) == col(TestSignup.innovation_id))
        .where(*filters)
    )
    rows = await session.exec(
        joined()
        .where(*filters)
        .order_by(col(TestSignup.created_at).desc())
        .offset(offset(page, per_page))
        .limit(per_page)
    )
    return Page(
        items=[admin_volunteer(*row) for row in rows],
        total=total or 0,
        page=page,
        per_page=per_page,
    )


async def counts(session: AsyncSession) -> VolunteerCounts:
    rows = await session.exec(
        select(TestSignup.status, func.count()).group_by(col(TestSignup.status))
    )
    return VolunteerCounts(**{str(status): count for status, count in rows})


def _rows(rows: Sequence[Any]) -> list[AdminVolunteer]:
    return [admin_volunteer(*row) for row in rows]


async def innovation_reports(
    session: AsyncSession, innovation: Innovation
) -> InnovationReports:
    rows = (
        await session.exec(
            joined()
            .where(
                TestSignup.innovation_id == innovation.id,
                col(VolunteerReport.id).is_not(None),
            )
            .order_by(col(VolunteerReport.updated_at).desc())
        )
    ).all()
    items = _rows(rows)
    recommend = RecommendCounts()
    for item in items:
        if item.report is not None:
            value = item.report.recommend.value
            setattr(recommend, value, getattr(recommend, value) + 1)
    return InnovationReports(
        innovation=InnovationRef.of(innovation),
        reports=len(items),
        participants=sum(item.report.participants for item in items if item.report),
        recommend=recommend,
        items=items,
    )


async def near_adaptation(
    session: AsyncSession, adaptation_id: uuid.UUID
) -> AdaptationVolunteers | None:
    row = (
        await session.exec(
            select(Adaptation, Innovation)
            .join(Innovation, col(Innovation.id) == col(Adaptation.innovation_id))
            .where(Adaptation.id == adaptation_id)
        )
    ).first()
    if row is None:
        return None
    adaptation, innovation = row
    items: list[AdminVolunteer] = []
    if adaptation.powiat:
        rows = (
            await session.exec(
                joined()
                .where(
                    TestSignup.innovation_id == innovation.id,
                    TestSignup.powiat == adaptation.powiat,
                    col(TestSignup.status).in_(NEAR_ADAPTATION),
                )
                .order_by(col(TestSignup.created_at).desc())
            )
        ).all()
        items = _rows(rows)
    return AdaptationVolunteers(
        innovation=InnovationRef.of(innovation),
        powiat=adaptation.powiat,
        powiat_name=powiat_label(adaptation.powiat),
        count=len(items),
        items=items,
    )
