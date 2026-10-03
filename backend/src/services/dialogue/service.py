import asyncio
import hashlib
import hmac
import uuid
from datetime import UTC, datetime

from sqlalchemy import Update, func, select, update
from sqlmodel import col
from sqlmodel import select as entity_select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import ApiError
from services.bus import bus
from services.mail import DeliveryStatus, Mailer, author_reply
from utils.db import session_scope
from utils.db.models import (
    AdminUser,
    Message,
    MessageDelivery,
    MessageDirection,
    Need,
    NeedStatus,
)
from utils.logging import logger

from .audit import record
from .inbox import admin_message, build
from .links import link_token_matches, thread_url
from .schemas import AdminMessage, PublicMessage

UNANSWERED_LIMIT = 10
DELIVERY_ERROR_LIMIT = 500

pending_deliveries: set[asyncio.Task[None]] = set()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_opens(need: Need, token: str | None) -> bool:
    if not token:
        return False
    if hmac.compare_digest(token_hash(token), need.edit_token_hash):
        return True
    return link_token_matches(need.id, token)


async def need_for_token(
    session: AsyncSession, need_id: uuid.UUID, token: str | None
) -> Need | None:
    need = await session.get(Need, need_id)
    if need is None or not token_opens(need, token):
        return None
    return need


def can_email(need: Need) -> bool:
    return bool(need.contact_email and need.contact_consent)


async def publish_need(session: AsyncSession, need: Need) -> None:
    payload = (await build(session, [need]))[0]
    bus.publish("need.updated", payload.model_dump(mode="json"))


def publish_message(topic: str, message: AdminMessage) -> None:
    bus.publish(topic, message.model_dump(mode="json"))


async def public_messages(
    session: AsyncSession, need_id: uuid.UUID
) -> list[PublicMessage]:
    result = await session.exec(
        entity_select(Message)
        .where(col(Message.need_id) == need_id)
        .order_by(col(Message.sent_at), col(Message.created_at))
    )
    return [
        PublicMessage(
            id=message.id,
            direction=message.direction,
            body=message.body,
            sent_at=message.sent_at,
        )
        for message in result.all()
    ]


async def set_status(
    session: AsyncSession, need: Need, admin: AdminUser, status: NeedStatus
) -> Need:
    previous = need.status
    if previous == status:
        return need
    need.status = status
    session.add(need)
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
    return need


def read_all(need_id: uuid.UUID) -> Update:
    return (
        update(Message)
        .where(
            col(Message.need_id) == need_id,
            col(Message.direction) == MessageDirection.FROM_AUTHOR,
            col(Message.read_at).is_(None),
        )
        .values(read_at=func.now())
    )


async def mark_read(session: AsyncSession, need_id: uuid.UUID) -> None:
    result = await session.exec(read_all(need_id))
    if result.rowcount:
        await session.commit()


async def reply(
    session: AsyncSession, need: Need, admin: AdminUser, body: str, mailer: Mailer
) -> AdminMessage:
    emailed = can_email(need)
    message = Message(
        need_id=need.id,
        direction=MessageDirection.TO_AUTHOR,
        body=body,
        admin_id=admin.id,
        delivery_status=MessageDelivery.PENDING if emailed else None,
    )
    session.add(message)
    previous = need.status
    need.status = NeedStatus.ANSWERED
    session.add(need)
    await session.flush()
    record(
        session,
        admin,
        "need.reply",
        target=("need", need.id),
        details={
            "message_id": str(message.id),
            "emailed": emailed,
            "from": previous.value,
        },
    )
    await session.exec(read_all(need.id))
    await session.commit()
    await session.refresh(message)
    await session.refresh(need)
    result = admin_message(message, admin.login)
    publish_message("message.created", result)
    await publish_need(session, need)
    if emailed:
        task = asyncio.create_task(deliver(message.id, mailer))
        pending_deliveries.add(task)
        task.add_done_callback(pending_deliveries.discard)
    return result


async def deliver(message_id: uuid.UUID, mailer: Mailer) -> None:
    try:
        async with session_scope() as session:
            message = await session.get(Message, message_id)
            if message is None or message.need_id is None:
                return
            need = await session.get(Need, message.need_id)
            if need is None or not can_email(need):
                return
            delivery = await mailer.send(
                author_reply(
                    to=str(need.contact_email),
                    need_text=need.text,
                    body=message.body,
                    thread_url=thread_url(need.id),
                    idempotency_key=f"message-{message.id}",
                )
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


async def unanswered_count(session: AsyncSession, need_id: uuid.UUID) -> int:
    last_reply = (
        select(func.max(col(Message.sent_at)))
        .where(
            col(Message.need_id) == need_id,
            col(Message.direction) == MessageDirection.TO_AUTHOR,
        )
        .scalar_subquery()
    )
    total = await session.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            col(Message.need_id) == need_id,
            col(Message.direction) == MessageDirection.FROM_AUTHOR,
            col(Message.sent_at)
            > func.coalesce(last_reply, datetime(1970, 1, 1, tzinfo=UTC)),
        )
    )
    return int(total or 0)


async def author_message(session: AsyncSession, need: Need, body: str) -> PublicMessage:
    if await unanswered_count(session, need.id) >= UNANSWERED_LIMIT:
        raise ApiError(
            429,
            "too_many_messages",
            "Wysłano już kilka wiadomości bez odpowiedzi. "
            "Poczekaj, aż ROPS odpowie, zanim napiszesz ponownie.",
        )
    message = Message(
        need_id=need.id, direction=MessageDirection.FROM_AUTHOR, body=body
    )
    session.add(message)
    if need.status != NeedStatus.NEW:
        need.status = NeedStatus.NEW
        session.add(need)
    await session.commit()
    await session.refresh(message)
    await session.refresh(need)
    publish_message("message.created", admin_message(message, None))
    await publish_need(session, need)
    return PublicMessage(
        id=message.id,
        direction=message.direction,
        body=message.body,
        sent_at=message.sent_at,
    )
