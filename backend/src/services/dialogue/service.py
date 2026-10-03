import asyncio
import hmac
import uuid
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, Update, func, select, update
from sqlmodel import col
from sqlmodel import select as entity_select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import ApiError
from services.bus import bus
from services.mail import (
    Delivery,
    DeliveryStatus,
    Email,
    Mailer,
    application_reply,
    author_reply,
    expert_message,
    idea_reply,
)
from services.needs import (
    attach_need,
    cluster_payload,
    detach_need,
    hash_token,
    schedule_summary,
)
from utils.db import session_scope
from utils.db.models import (
    AdminUser,
    GrantApplication,
    GrantCall,
    Idea,
    Message,
    MessageDelivery,
    MessageDirection,
    Need,
    NeedStatus,
)
from utils.logging import logger

from .audit import record
from .inbox import admin_message, admin_messages, build, expert_ref
from .links import IDEA_CONTEXT, NEED_CONTEXT, idea_thread_url, link_token_matches
from .links import thread_url as need_thread_url
from .schemas import AdminMessage, PublicMessage

UNANSWERED_LIMIT = 10
DELIVERY_ERROR_LIMIT = 500
TOO_MANY = (
    "Wysłano już kilka wiadomości bez odpowiedzi. "
    "Poczekaj, aż ROPS odpowie, zanim napiszesz ponownie."
)

type Owner = Need | Idea | GrantApplication
type Thread = Need | Idea

background: set[asyncio.Task[Any]] = set()


def spawn(job: Coroutine[Any, Any, Any]) -> None:
    task = asyncio.create_task(job)
    background.add(task)
    task.add_done_callback(background.discard)


def owned_by(owner: Owner) -> ColumnElement[bool]:
    if isinstance(owner, GrantApplication):
        return col(Message.application_id) == owner.id
    if isinstance(owner, Idea):
        return col(Message.idea_id) == owner.id
    return col(Message.need_id) == owner.id


def token_opens(owner: Thread, token: str | None) -> bool:
    if not token:
        return False
    if hmac.compare_digest(hash_token(token), owner.edit_token_hash):
        return True
    context = IDEA_CONTEXT if isinstance(owner, Idea) else NEED_CONTEXT
    return link_token_matches(owner.id, token, context)


async def need_for_token(
    session: AsyncSession, need_id: uuid.UUID, token: str | None
) -> Need | None:
    need = await session.get(Need, need_id)
    return need if need is not None and token_opens(need, token) else None


async def idea_for_token(
    session: AsyncSession, idea_id: uuid.UUID, token: str | None
) -> Idea | None:
    idea = await session.get(Idea, idea_id)
    return idea if idea is not None and token_opens(idea, token) else None


def can_email(owner: Owner) -> bool:
    return bool(owner.contact_email and owner.contact_consent)


async def publish_need(session: AsyncSession, need: Need) -> None:
    payload = (await build(session, [need]))[0]
    bus.publish("need.updated", payload.model_dump(mode="json"))


def publish_message(topic: str, message: AdminMessage) -> None:
    bus.publish(topic, message.model_dump(mode="json"))


def public_message(message: Message) -> PublicMessage:
    expert = expert_ref(message)
    if message.direction == MessageDirection.FROM_AUTHOR:
        author = "author"
    else:
        author = "expert" if expert else "rops"
    return PublicMessage(
        id=message.id,
        direction=message.direction,
        body=message.body,
        sent_at=message.sent_at,
        author=author,
        expert=expert,
    )


async def public_messages(session: AsyncSession, owner: Owner) -> list[PublicMessage]:
    result = await session.exec(
        entity_select(Message)
        .where(owned_by(owner))
        .order_by(col(Message.sent_at), col(Message.created_at))
    )
    return [public_message(message) for message in result.all()]


async def thread_for_admin(session: AsyncSession, owner: Owner) -> list[AdminMessage]:
    return await admin_messages(session, owned_by(owner))


async def set_status(
    session: AsyncSession, need: Need, admin: AdminUser, status: NeedStatus
) -> Need:
    previous = need.status
    if previous == status:
        return need
    need.status = status
    session.add(need)
    changed = None
    if status == NeedStatus.JUNK:
        changed = await detach_need(session, need)
    elif previous == NeedStatus.JUNK:
        changed = await attach_need(session, need)
    record(
        session,
        admin,
        "need.status",
        target=("need", need.id),
        details={"from": previous.value, "to": status.value},
    )
    await session.commit()
    await session.refresh(need)
    await publish_need(session, need)
    if changed is not None:
        await session.refresh(changed)
        bus.publish("cluster.updated", cluster_payload(changed))
        if changed.summary_stale:
            schedule_summary(changed.id)
    return need


def read_all(owner: Owner) -> Update:
    return (
        update(Message)
        .where(
            owned_by(owner),
            col(Message.direction) == MessageDirection.FROM_AUTHOR,
            col(Message.read_at).is_(None),
        )
        .values(read_at=func.now())
    )


async def mark_read(session: AsyncSession, owner: Owner) -> None:
    result = await session.exec(read_all(owner))
    if result.rowcount:
        await session.commit()


async def reply(
    session: AsyncSession, owner: Owner, admin: AdminUser, body: str, mailer: Mailer
) -> AdminMessage:
    emailed = can_email(owner)
    is_idea = isinstance(owner, Idea)
    is_application = isinstance(owner, GrantApplication)
    message = Message(
        need_id=owner.id if isinstance(owner, Need) else None,
        idea_id=owner.id if is_idea else None,
        application_id=owner.id if is_application else None,
        direction=MessageDirection.TO_AUTHOR,
        body=body,
        admin_id=admin.id,
        delivery_status=MessageDelivery.PENDING if emailed else None,
    )
    session.add(message)
    details: dict[str, Any] = {"emailed": emailed}
    if isinstance(owner, Need):
        details["from"] = owner.status.value
        if owner.status != NeedStatus.JUNK:
            owner.status = NeedStatus.ANSWERED
        session.add(owner)
    await session.flush()
    details["message_id"] = str(message.id)
    kind = "application" if is_application else "idea" if is_idea else "need"
    record(
        session,
        admin,
        f"{kind}.reply",
        target=("grant_application" if is_application else kind, owner.id),
        details=details,
    )
    await session.exec(read_all(owner))
    await session.commit()
    await session.refresh(message)
    result = admin_message(message, admin.login)
    publish_message("message.created", result)
    if isinstance(owner, Need):
        await session.refresh(owner)
        await publish_need(session, owner)
    if emailed:
        spawn(deliver(message.id, mailer))
    return result


def reply_email(owner: Owner, message: Message, call_title: str = "") -> Email:
    key = f"message-{message.id}"
    if isinstance(owner, GrantApplication):
        return application_reply(
            to=str(owner.contact_email),
            application_number=owner.number or 0,
            call_title=call_title,
            body=message.body,
            idempotency_key=key,
        )
    if message.expert_name:
        is_idea = isinstance(owner, Idea)
        return expert_message(
            to=str(owner.contact_email),
            about=owner.title if isinstance(owner, Idea) else owner.text,
            is_idea=is_idea,
            expert_name=message.expert_name,
            expertise=message.expert_field,
            body=message.body,
            thread_url=idea_thread_url(owner.id)
            if is_idea
            else need_thread_url(owner.id),
            idempotency_key=key,
        )
    if isinstance(owner, Idea):
        return idea_reply(
            to=str(owner.contact_email),
            idea_title=owner.title,
            body=message.body,
            thread_url=idea_thread_url(owner.id),
            idempotency_key=key,
        )
    return author_reply(
        to=str(owner.contact_email),
        need_text=owner.text,
        body=message.body,
        thread_url=need_thread_url(owner.id),
        idempotency_key=key,
    )


async def owner_of(session: AsyncSession, message: Message) -> Owner | None:
    if message.application_id is not None:
        return await session.get(GrantApplication, message.application_id)
    if message.idea_id is not None:
        return await session.get(Idea, message.idea_id)
    if message.need_id is not None:
        return await session.get(Need, message.need_id)
    return None


async def deliver(message_id: uuid.UUID, mailer: Mailer) -> None:
    try:
        async with session_scope() as session:
            message = await session.get(Message, message_id)
            owner = None if message is None else await owner_of(session, message)
            if message is None or owner is None:
                return
            call = (
                await session.get(GrantCall, owner.call_id)
                if isinstance(owner, GrantApplication)
                else None
            )
            delivery = (
                await mailer.send(
                    reply_email(owner, message, call.title if call else "")
                )
                if can_email(owner)
                else Delivery(DeliveryStatus.SKIPPED, error="no contact consent")
            )
            message.delivery_status = MessageDelivery(delivery.status.value)
            message.provider_id = delivery.provider_id
            message.delivery_error = (
                delivery.error[:DELIVERY_ERROR_LIMIT] if delivery.error else None
            )
            session.add(message)
            await session.commit()
            await session.refresh(message)
            login = None
            if message.admin_id:
                admin = await session.get(AdminUser, message.admin_id)
                login = admin.login if admin else None
            publish_message("message.updated", admin_message(message, login))
            if delivery.status == DeliveryStatus.FAILED:
                logger.warning("reply %s not delivered", message.id)
    except Exception:
        logger.exception("reply delivery crashed for %s", message_id)


async def resume_pending(mailer: Mailer) -> int:
    try:
        async with session_scope() as session:
            result = await session.exec(
                entity_select(Message.id).where(
                    col(Message.delivery_status) == MessageDelivery.PENDING
                )
            )
            pending = list(result.all())
    except Exception:
        logger.exception("cannot resume pending reply emails")
        return 0
    for message_id in pending:
        spawn(deliver(message_id, mailer))
    if pending:
        logger.info("resuming %d pending reply emails", len(pending))
    return len(pending)


async def unanswered_count(session: AsyncSession, owner: Owner) -> int:
    last_reply = (
        select(func.max(col(Message.sent_at)))
        .where(owned_by(owner), col(Message.direction) == MessageDirection.TO_AUTHOR)
        .scalar_subquery()
    )
    total = await session.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            owned_by(owner),
            col(Message.direction) == MessageDirection.FROM_AUTHOR,
            col(Message.sent_at)
            > func.coalesce(last_reply, datetime(1970, 1, 1, tzinfo=UTC)),
        )
    )
    return int(total or 0)


async def author_message(
    session: AsyncSession, owner: Owner, body: str
) -> PublicMessage:
    if await unanswered_count(session, owner) >= UNANSWERED_LIMIT:
        raise ApiError(429, "too_many_messages", TOO_MANY)
    is_idea = isinstance(owner, Idea)
    message = Message(
        need_id=None if is_idea else owner.id,
        idea_id=owner.id if is_idea else None,
        direction=MessageDirection.FROM_AUTHOR,
        body=body,
    )
    session.add(message)
    if isinstance(owner, Need) and owner.status not in {
        NeedStatus.NEW,
        NeedStatus.JUNK,
    }:
        owner.status = NeedStatus.NEW
        session.add(owner)
    await session.commit()
    await session.refresh(message)
    publish_message("message.created", admin_message(message, None))
    if isinstance(owner, Need):
        await session.refresh(owner)
        await publish_need(session, owner)
    return public_message(message)
