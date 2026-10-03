import asyncio
import uuid
from datetime import UTC, datetime
from html import escape
from zoneinfo import ZoneInfo

from sqlalchemy import update
from sqlmodel import col
from sqlmodel import select as entity_select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.mail import DeliveryStatus, Email, Mailer
from services.mail.templates import (
    H1,
    SIGNATURE,
    excerpt,
    html_button,
    html_document,
    html_paragraphs,
)
from services.modules import normalize_email
from services.signing import key_matches, signed_key
from utils.db import session_scope
from utils.db.models import GrantCall, GrantSubscriber
from utils.env import env
from utils.logging import logger

from .calls import due_for_open_notice

CONFIRM = "grant-sub-confirm"
UNSUBSCRIBE = "grant-sub-unsubscribe"
WATCH_SECONDS = 60.0
WARSAW = ZoneInfo("Europe/Warsaw")
NOTE = (
    "Dostajesz tę wiadomość, bo zapisano ten adres na powiadomienia o naborach w HubMi."
)


class InvalidEmailError(ValueError):
    pass


def token(context: str, subscriber_id: uuid.UUID) -> str:
    return f"{subscriber_id}.{signed_key(context, subscriber_id)}"


def token_owner(context: str, value: str) -> uuid.UUID | None:
    raw_id, _, key = value.partition(".")
    try:
        subscriber_id = uuid.UUID(raw_id)
    except ValueError:
        return None
    return subscriber_id if key_matches(key, context, subscriber_id) else None


def page_url(fragment: str) -> str:
    return f"{env.mailer.public_url.rstrip('/')}/nabory/powiadomienia#{fragment}"


def calls_url(call_id: uuid.UUID | None = None) -> str:
    base = f"{env.mailer.public_url.rstrip('/')}/nabory"
    return f"{base}/{call_id}" if call_id else base


def local(moment: datetime) -> str:
    return moment.astimezone(WARSAW).strftime("%d.%m.%Y, godz. %H:%M")


def confirm_email(subscriber: GrantSubscriber) -> Email:
    url = page_url(f"confirm={token(CONFIRM, subscriber.id)}")
    subject = "Potwierdź powiadomienia o naborach w HubMi"
    text = (
        "Dzień dobry,\n\n"
        "ktoś (zapewne Ty) poprosił o powiadomienia o naborach grantowych ROPS "
        "w Krakowie w HubMi. Aby je włączyć, otwórz link:\n"
        f"{url}\n\n"
        "Jeśli to nie Ty, zignoruj tę wiadomość: bez potwierdzenia nic więcej "
        "nie wyślemy.\n\n"
        f"{SIGNATURE}"
    )
    html = html_document(
        subject,
        f"{H1}Potwierdź powiadomienia</h1>"
        '<p style="margin:0 0 16px">Ktoś (zapewne Ty) poprosił o powiadomienia '
        "o naborach grantowych ROPS w Krakowie w HubMi.</p>"
        f"{html_button(url, 'Potwierdzam')}"
        '<p style="margin:0 0 16px">Jeśli to nie Ty, zignoruj tę wiadomość: '
        "bez potwierdzenia nic więcej nie wyślemy.</p>"
        f"{html_paragraphs(SIGNATURE)}",
    )
    return Email(
        to=subscriber.email,
        subject=subject,
        text=text,
        html=html,
        idempotency_key=f"grant-confirm-{subscriber.id}-{int(subscriber.updated_at.timestamp())}",
    )


def call_email(call: GrantCall, subscriber: GrantSubscriber, *, opened: bool) -> Email:
    stop = page_url(f"unsubscribe={token(UNSUBSCRIBE, subscriber.id)}")
    url = calls_url(call.id)
    if opened:
        subject = f"Otwarty nabór: {excerpt(call.title, 120)}"
        lead = "W HubMi otworzył się nabór, w którym możesz złożyć wniosek."
    else:
        subject = f"Zmiana terminów naboru: {excerpt(call.title, 120)}"
        lead = "ROPS zmienił terminy naboru, o którym informowaliśmy."
    dates = f"Nabór trwa od {local(call.opens_at)} do {local(call.closes_at)}."
    text = (
        f"Dzień dobry,\n\n{lead}\n\n„{call.title}”\n{dates}\n\n"
        f"Szczegóły i wniosek: {url}\n\n{SIGNATURE}\n\n{NOTE}\n"
        f"Wypisz się: {stop}"
    )
    html = html_document(
        subject,
        f"{H1}{escape(subject)}</h1>"
        f'<p style="margin:0 0 16px">{escape(lead)}</p>'
        f'<p style="margin:0 0 16px"><strong>{escape(call.title)}</strong><br>'
        f"{escape(dates)}</p>"
        f"{html_button(url, 'Zobacz nabór')}"
        f"{html_paragraphs(SIGNATURE)}"
        '<p style="margin:24px 0 0;font-size:13px;color:#57534e">'
        f'{NOTE} <a href="{escape(stop)}">Wypisz się</a>.</p>',
    )
    kind = "open" if opened else f"dates-{int(call.updated_at.timestamp())}"
    return Email(
        to=subscriber.email,
        subject=subject,
        text=text,
        html=html,
        idempotency_key=f"grant-{call.id}-{kind}-{subscriber.id}",
    )


async def subscribe(
    session: AsyncSession, email: str, mailer: Mailer
) -> GrantSubscriber | None:
    address = normalize_email(email)
    if address is None:
        raise InvalidEmailError
    address = address.lower()
    rows = await session.exec(
        entity_select(GrantSubscriber).where(col(GrantSubscriber.email) == address)
    )
    subscriber = rows.first()
    moment = datetime.now(UTC)
    if (
        subscriber is not None
        and subscriber.confirmed_at
        and not (subscriber.unsubscribed_at)
    ):
        return None
    if subscriber is None:
        subscriber = GrantSubscriber(email=address, consent_at=moment)
    else:
        subscriber.consent_at = moment
        subscriber.confirmed_at = None
        subscriber.unsubscribed_at = None
        subscriber.updated_at = moment
    session.add(subscriber)
    await session.commit()
    await session.refresh(subscriber)
    await mailer.send(confirm_email(subscriber))
    return subscriber


async def confirm(session: AsyncSession, value: str) -> bool:
    subscriber_id = token_owner(CONFIRM, value)
    subscriber = (
        await session.get(GrantSubscriber, subscriber_id) if subscriber_id else None
    )
    if subscriber is None:
        return False
    if subscriber.unsubscribed_at is None:
        subscriber.confirmed_at = subscriber.confirmed_at or datetime.now(UTC)
        session.add(subscriber)
        await session.commit()
    return subscriber.unsubscribed_at is None


async def unsubscribe(session: AsyncSession, value: str) -> bool:
    subscriber_id = token_owner(UNSUBSCRIBE, value) or token_owner(CONFIRM, value)
    subscriber = (
        await session.get(GrantSubscriber, subscriber_id) if subscriber_id else None
    )
    if subscriber is None:
        return False
    subscriber.unsubscribed_at = subscriber.unsubscribed_at or datetime.now(UTC)
    session.add(subscriber)
    await session.commit()
    return True


async def notify(call_id: uuid.UUID, mailer: Mailer, *, opened: bool) -> int:
    sent = 0
    total = 0
    async with session_scope() as session:
        call = await session.get(GrantCall, call_id)
        if call is None:
            return 0
        rows = await session.exec(
            entity_select(GrantSubscriber).where(
                col(GrantSubscriber.confirmed_at).is_not(None),
                col(GrantSubscriber.unsubscribed_at).is_(None),
            )
        )
        subscribers = list(rows.all())
        total = len(subscribers)
        for subscriber in subscribers:
            try:
                delivery = await mailer.send(
                    call_email(call, subscriber, opened=opened)
                )
                if delivery.status == DeliveryStatus.SENT:
                    sent += 1
            except Exception:
                logger.exception("call mail failed for %s", subscriber.id)
    logger.info("grant call %s: %d subscribers notified", call_id, sent)
    return sent if sent == total else -1


async def mark_open_notice(session: AsyncSession, call_id: uuid.UUID) -> bool:
    result = await session.exec(
        update(GrantCall)
        .where(col(GrantCall.id) == call_id, col(GrantCall.notified_open_at).is_(None))
        .values(notified_open_at=datetime.now(UTC))
        .returning(col(GrantCall.id))
    )
    claimed = result.scalar_one_or_none() is not None
    await session.commit()
    return claimed


async def watch_calls(mailer: Mailer) -> None:
    while True:
        try:
            async with session_scope() as session:
                due = [call.id for call in await due_for_open_notice(session)]
            for call_id in due:
                sent = await notify(call_id, mailer, opened=True)
                if sent >= 0:
                    async with session_scope() as session:
                        await mark_open_notice(session, call_id)
        except Exception:
            logger.exception("grant call watch failed")
        await asyncio.sleep(WATCH_SECONDS)
