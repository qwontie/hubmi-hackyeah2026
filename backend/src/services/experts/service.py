import uuid
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, func, select
from sqlmodel import col
from sqlmodel import select as entity_select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.bus import bus
from services.dialogue.audit import record
from services.dialogue.inbox import admin_message, admin_messages
from services.dialogue.service import can_email, deliver, owned_by, spawn
from services.kreator import repository as ideas
from services.mail import Mailer, expert_assigned
from services.mail.templates import excerpt
from utils.db.models import (
    AdminRole,
    AdminUser,
    Assignment,
    AssignmentStatus,
    ExpertNote,
    Idea,
    Message,
    MessageDelivery,
    MessageDirection,
    Need,
)
from utils.env import env
from utils.logging import logger

from .schemas import (
    AdminAssignment,
    AssignmentOut,
    ExpertAssignmentDetail,
    ExpertBrief,
    ExpertOut,
    NeedItem,
    NoteOut,
    OpinionOut,
)

type Item = Need | Idea


class AlreadyAssignedError(RuntimeError):
    pass


class NotAnExpertError(RuntimeError):
    pass


def item_title(item: Item) -> str:
    if isinstance(item, Idea):
        return f"Pomysł nr {item.number}: {item.title}"
    return f"Zgłoszenie nr {item.number}: {item.title or excerpt(item.text, 120)}"


def panel_url(assignment_id: uuid.UUID) -> str:
    return f"{env.mailer.public_url.rstrip('/')}/admin/expert/{assignment_id}"


async def experts(session: AsyncSession) -> list[ExpertOut]:
    counts = (
        select(
            col(Assignment.expert_id),
            func.count()
            .filter(col(Assignment.status) == AssignmentStatus.OPEN)
            .label("open"),
            func.count()
            .filter(col(Assignment.status) == AssignmentStatus.ANSWERED)
            .label("answered"),
        )
        .group_by(col(Assignment.expert_id))
        .subquery()
    )
    rows = await session.exec(
        entity_select(AdminUser, counts.c.open, counts.c.answered)
        .outerjoin(counts, counts.c.expert_id == col(AdminUser.id))
        .where(col(AdminUser.role) == AdminRole.EXPERT)
        .order_by(col(AdminUser.display_name), col(AdminUser.login))
    )
    return [
        ExpertOut(
            id=user.id,
            login=user.login,
            display_name=user.display_name,
            expertise=user.expertise,
            has_email=bool(user.email),
            open=int(open_ or 0),
            answered=int(answered or 0),
        )
        for user, open_, answered in rows.all()
    ]


async def item_of(session: AsyncSession, assignment: Assignment) -> Item | None:
    if assignment.idea_id is not None:
        return await session.get(Idea, assignment.idea_id)
    if assignment.need_id is not None:
        return await session.get(Need, assignment.need_id)
    return None


async def opinions_count(session: AsyncSession, assignment: Assignment) -> int:
    if assignment.expert_id is None:
        answers = await session.scalar(
            select(func.count())
            .select_from(ExpertNote)
            .where(col(ExpertNote.assignment_id) == assignment.id)
        )
        return int(answers or 0)
    owner = (
        col(Message.idea_id) == assignment.idea_id
        if assignment.idea_id
        else col(Message.need_id) == assignment.need_id
    )
    total = await session.scalar(
        select(func.count())
        .select_from(Message)
        .where(owner, col(Message.admin_id) == assignment.expert_id)
    )
    return int(total or 0)


async def brief(session: AsyncSession, assignment: Assignment) -> ExpertBrief:
    if assignment.expert_id is None:
        return ExpertBrief(
            id=None,
            display_name=assignment.expert_name,
            expertise=assignment.expert_field,
            email=assignment.expert_email,
        )
    expert = await session.get(AdminUser, assignment.expert_id)
    return ExpertBrief(
        id=assignment.expert_id,
        display_name=expert.display_name if expert else None,
        expertise=expert.expertise if expert else None,
    )


async def out(session: AsyncSession, assignment: Assignment) -> AssignmentOut:
    item = await item_of(session, assignment)
    return AssignmentOut(
        id=assignment.id,
        kind="idea" if assignment.idea_id else "need",
        need_id=assignment.need_id,
        idea_id=assignment.idea_id,
        title=item_title(item) if item else "",
        expert=await brief(session, assignment),
        note=assignment.note,
        status=assignment.status,
        assigned_by=assignment.assigned_by,
        opinions_count=await opinions_count(session, assignment),
        delivery_status=assignment.delivery_status,
        created_at=assignment.created_at,
        answered_at=assignment.answered_at,
    )


async def notes(session: AsyncSession, assignment_id: uuid.UUID) -> list[NoteOut]:
    rows = await session.exec(
        entity_select(ExpertNote)
        .where(col(ExpertNote.assignment_id) == assignment_id)
        .order_by(col(ExpertNote.created_at))
    )
    return [NoteOut(id=n.id, body=n.body, created_at=n.created_at) for n in rows]


async def admin_view(session: AsyncSession, assignment: Assignment) -> AdminAssignment:
    return AdminAssignment(
        **(await out(session, assignment)).model_dump(),
        private_notes=await notes(session, assignment.id),
    )


def owner_filter(item: Item) -> ColumnElement[bool]:
    if isinstance(item, Idea):
        return col(Assignment.idea_id) == item.id
    return col(Assignment.need_id) == item.id


async def for_item(session: AsyncSession, item: Item) -> list[AdminAssignment]:
    rows = await session.exec(
        entity_select(Assignment)
        .where(owner_filter(item))
        .order_by(col(Assignment.created_at))
    )
    return [await admin_view(session, a) for a in rows.all()]


async def assign(  # noqa: PLR0913
    session: AsyncSession,
    *,
    admin: AdminUser,
    item: Item,
    expert_id: uuid.UUID,
    note: str | None,
    mailer: Mailer,
) -> AssignmentOut:
    expert = await session.get(AdminUser, expert_id)
    if expert is None or expert.role != AdminRole.EXPERT:
        raise NotAnExpertError
    existing = await session.exec(
        entity_select(Assignment.id).where(
            owner_filter(item), col(Assignment.expert_id) == expert_id
        )
    )
    if existing.first() is not None:
        raise AlreadyAssignedError
    is_idea = isinstance(item, Idea)
    assignment = Assignment(
        expert_id=expert_id,
        idea_id=item.id if is_idea else None,
        need_id=None if is_idea else item.id,
        note=note or None,
        assigned_by=admin.login,
    )
    session.add(assignment)
    await session.flush()
    record(
        session,
        admin,
        "assignment.create",
        target=("idea" if is_idea else "need", item.id),
        details={"assignment_id": str(assignment.id), "expert": expert.login},
    )
    await session.commit()
    await session.refresh(assignment)
    result = await out(session, assignment)
    bus.publish("assignment.created", result.model_dump(mode="json"))
    if expert.email:
        spawn(
            send_quietly(
                mailer,
                expert.email,
                expert.display_name or expert.login,
                result.title,
                assignment,
            )
        )
    return result


async def send_quietly(
    mailer: Mailer, to: str, name: str, title: str, assignment: Assignment
) -> None:
    try:
        await mailer.send(
            expert_assigned(
                to=to,
                expert_name=name,
                title=title,
                note=assignment.note,
                url=panel_url(assignment.id),
                key=f"assignment-{assignment.id}",
            )
        )
    except Exception:
        logger.exception("assignment mail failed for %s", assignment.id)


async def unassign(
    session: AsyncSession, admin: AdminUser, assignment: Assignment
) -> None:
    record(
        session,
        admin,
        "assignment.delete",
        target=(
            "idea" if assignment.idea_id else "need",
            assignment.idea_id or assignment.need_id,
        ),
        details={"assignment_id": str(assignment.id)},
    )
    await session.delete(assignment)
    await session.commit()


async def for_expert(
    session: AsyncSession, expert: AdminUser, status: AssignmentStatus | None
) -> list[AssignmentOut]:
    query = entity_select(Assignment).where(col(Assignment.expert_id) == expert.id)
    if status is not None:
        query = query.where(col(Assignment.status) == status)
    rows = await session.exec(
        query.order_by(col(Assignment.status).desc(), col(Assignment.created_at).desc())
    )
    return [await out(session, a) for a in rows.all()]


def need_item(need: Need) -> NeedItem:
    return NeedItem(
        id=need.id,
        number=need.number,
        text=need.text,
        title=need.title,
        powiat=need.powiat,
        category_slug=need.category_slug,
        status=need.status,
        created_at=need.created_at,
    )


async def detail(
    session: AsyncSession, assignment: Assignment
) -> ExpertAssignmentDetail | None:
    item = await item_of(session, assignment)
    if item is None:
        return None
    view = ideas.author_view(item) if isinstance(item, Idea) else need_item(item)
    return ExpertAssignmentDetail(
        **(await admin_view(session, assignment)).model_dump(),
        item=view,
        messages=await admin_messages(session, owned_by(item)),
    )


async def opinion(  # noqa: PLR0913
    session: AsyncSession,
    *,
    expert: AdminUser,
    assignment: Assignment,
    body: str | None,
    private_note: str | None,
    mailer: Mailer,
) -> OpinionOut | None:
    item = await item_of(session, assignment)
    if item is None:
        return None
    is_idea = isinstance(item, Idea)
    message = None
    note = None
    emailed = False
    if body:
        emailed = can_email(item)
        message = Message(
            need_id=None if is_idea else item.id,
            idea_id=item.id if is_idea else None,
            direction=MessageDirection.TO_AUTHOR,
            body=body,
            admin_id=expert.id,
            delivery_status=MessageDelivery.PENDING if emailed else None,
            expert_name=expert.display_name or "Ekspert",
            expert_field=expert.expertise,
        )
        session.add(message)
        assignment.status = AssignmentStatus.ANSWERED
        assignment.answered_at = assignment.answered_at or datetime.now(UTC)
        session.add(assignment)
    if private_note:
        note = ExpertNote(assignment_id=assignment.id, body=private_note)
        session.add(note)
    await session.flush()
    record(
        session,
        expert,
        "expert.opinion",
        target=("idea" if is_idea else "need", item.id),
        details={
            "assignment_id": str(assignment.id),
            "message_id": str(message.id) if message else None,
            "private_note": note is not None,
            "emailed": emailed,
        },
    )
    await session.commit()
    message_out = None
    if message is not None:
        await session.refresh(message)
        message_out = admin_message(message, expert.login)
        bus.publish("message.created", message_out.model_dump(mode="json"))
        if emailed:
            spawn(deliver(message.id, mailer))
    note_out = None
    if note is not None:
        await session.refresh(note)
        note_out = NoteOut(id=note.id, body=note.body, created_at=note.created_at)
    await session.refresh(assignment)
    result = await out(session, assignment)
    if message is not None:
        bus.publish("assignment.answered", result.model_dump(mode="json"))
    return OpinionOut(message=message_out, private_note=note_out, assignment=result)
