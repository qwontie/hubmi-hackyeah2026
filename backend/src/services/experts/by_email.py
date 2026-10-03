import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy import select as sa_select
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.bus import bus
from services.dialogue.audit import record
from services.kreator import repository as ideas
from services.mail import Mailer
from services.mail.templates import expert_forwarded
from services.signing import key_matches, signed_key
from utils.db.models import AdminUser, Assignment, AssignmentStatus, ExpertNote, Idea
from utils.env import env

from .schemas import AssignmentOut, ExpertAnswerView, ExpertContact, NoteOut
from .service import (
    AlreadyAssignedError,
    Item,
    brief,
    item_of,
    item_title,
    need_item,
    out,
    owner_filter,
)

ANSWER_LINK = "expert-answer"
MAX_ANSWERS = 10


class NotByEmailError(RuntimeError):
    pass


class TooManyAnswersError(RuntimeError):
    pass


def answer_token(assignment_id: uuid.UUID) -> str:
    return signed_key(ANSWER_LINK, assignment_id)


def token_opens(assignment_id: uuid.UUID, token: str | None) -> bool:
    return key_matches(token, ANSWER_LINK, assignment_id)


def answer_url(assignment_id: uuid.UUID) -> str:
    base = env.mailer.public_url.rstrip("/")
    return f"{base}/ekspert/{assignment_id}#token={answer_token(assignment_id)}"


async def deliver(
    session: AsyncSession, assignment: Assignment, item: Item, mailer: Mailer
) -> None:
    delivery = await mailer.send(
        expert_forwarded(
            to=str(assignment.expert_email),
            expert_name=assignment.expert_name,
            title=item_title(item),
            note=assignment.note,
            url=answer_url(assignment.id),
            key=f"forward-{assignment.id}-{datetime.now(UTC).timestamp():.0f}",
        )
    )
    assignment.delivery_status = delivery.status.value
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)


async def forward(  # noqa: PLR0913
    session: AsyncSession,
    *,
    admin: AdminUser,
    item: Item,
    email: str,
    name: str | None,
    expertise: str | None,
    note: str | None,
    mailer: Mailer,
) -> AssignmentOut:
    existing = await session.exec(
        select(Assignment.id).where(
            owner_filter(item),
            func.lower(col(Assignment.expert_email)) == email.lower(),
        )
    )
    if existing.first() is not None:
        raise AlreadyAssignedError
    is_idea = isinstance(item, Idea)
    assignment = Assignment(
        expert_email=email,
        expert_name=name or None,
        expert_field=expertise or None,
        idea_id=item.id if is_idea else None,
        need_id=None if is_idea else item.id,
        note=note or None,
        assigned_by=admin.login,
        delivery_status="pending",
    )
    session.add(assignment)
    try:
        await session.flush()
        record(
            session,
            admin,
            "assignment.forward",
            target=("idea" if is_idea else "need", item.id),
            details={"assignment_id": str(assignment.id)},
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AlreadyAssignedError from None
    await session.refresh(assignment)
    await deliver(session, assignment, item, mailer)
    result = await out(session, assignment)
    bus.publish("assignment.created", result.model_dump(mode="json"))
    return result


async def resend(
    session: AsyncSession, admin: AdminUser, assignment: Assignment, mailer: Mailer
) -> AssignmentOut | None:
    if assignment.expert_email is None:
        raise NotByEmailError
    item = await item_of(session, assignment)
    if item is None:
        return None
    record(
        session,
        admin,
        "assignment.resend",
        target=("idea" if assignment.idea_id else "need", item.id),
        details={"assignment_id": str(assignment.id)},
    )
    await deliver(session, assignment, item, mailer)
    return await out(session, assignment)


async def contacts(session: AsyncSession) -> list[ExpertContact]:
    email = func.lower(col(Assignment.expert_email))
    connection = await session.connection()
    rows = await connection.execute(
        sa_select(
            email,
            func.max(col(Assignment.expert_name)),
            func.max(col(Assignment.expert_field)),
            func.count(),
            func.max(col(Assignment.created_at)),
        )
        .where(col(Assignment.expert_email).is_not(None))
        .group_by(email)
        .order_by(func.max(col(Assignment.created_at)).desc())
    )
    return [
        ExpertContact(
            email=address,
            name=name,
            expertise=field,
            assignments=total,
            last_at=last_at,
        )
        for address, name, field, total, last_at in rows.all()
    ]


async def answers(session: AsyncSession, assignment_id: uuid.UUID) -> list[NoteOut]:
    rows = await session.exec(
        select(ExpertNote)
        .where(col(ExpertNote.assignment_id) == assignment_id)
        .order_by(col(ExpertNote.created_at))
    )
    return [NoteOut(id=n.id, body=n.body, created_at=n.created_at) for n in rows]


async def opened(
    session: AsyncSession, assignment_id: uuid.UUID, token: str | None
) -> Assignment | None:
    if not token_opens(assignment_id, token):
        return None
    assignment = await session.get(Assignment, assignment_id)
    if assignment is None or assignment.expert_email is None:
        return None
    return assignment


async def view(
    session: AsyncSession, assignment: Assignment
) -> ExpertAnswerView | None:
    item = await item_of(session, assignment)
    if item is None:
        return None
    return ExpertAnswerView(
        id=assignment.id,
        kind="idea" if assignment.idea_id else "need",
        title=item_title(item),
        item=ideas.author_view(item) if isinstance(item, Idea) else need_item(item),
        note=assignment.note,
        expert=(await brief(session, assignment)).model_copy(update={"email": None}),
        status=AssignmentStatus(assignment.status),
        answers=await answers(session, assignment.id),
    )


async def answer(
    session: AsyncSession, assignment: Assignment, body: str
) -> ExpertAnswerView | None:
    count = await session.scalar(
        select(func.count())
        .select_from(ExpertNote)
        .where(col(ExpertNote.assignment_id) == assignment.id)
    )
    if (count or 0) >= MAX_ANSWERS:
        raise TooManyAnswersError
    session.add(ExpertNote(assignment_id=assignment.id, body=body))
    assignment.status = AssignmentStatus.ANSWERED
    assignment.answered_at = assignment.answered_at or datetime.now(UTC)
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    result = await out(session, assignment)
    bus.publish("assignment.answered", result.model_dump(mode="json"))
    return await view(session, assignment)
