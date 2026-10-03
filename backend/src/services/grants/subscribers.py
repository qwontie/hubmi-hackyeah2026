import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import GrantNoticeDelivery, GrantNoticeStatus, GrantSubscriber

SubscriberState = Literal["pending", "confirmed", "unsubscribed"]


class AdminSubscriber(BaseModel):
    id: uuid.UUID
    email: str
    state: SubscriberState
    consent_at: datetime
    confirmed_at: datetime | None
    unsubscribed_at: datetime | None
    created_at: datetime
    sent: int
    failed: int


class SubscriberTotals(BaseModel):
    confirmed: int
    pending: int
    unsubscribed: int
    failed_deliveries: int


class SubscriberList(BaseModel):
    items: list[AdminSubscriber]
    totals: SubscriberTotals


def state_of(subscriber: GrantSubscriber) -> SubscriberState:
    if subscriber.unsubscribed_at is not None:
        return "unsubscribed"
    return "confirmed" if subscriber.confirmed_at is not None else "pending"


async def list_subscribers(session: AsyncSession) -> SubscriberList:
    subscribers = (
        await session.exec(
            select(GrantSubscriber).order_by(col(GrantSubscriber.created_at).desc())
        )
    ).all()
    deliveries = {
        (subscriber_id, status): int(count)
        for subscriber_id, status, count in (
            await session.exec(
                select(
                    col(GrantNoticeDelivery.subscriber_id),
                    col(GrantNoticeDelivery.status),
                    func.count(),
                ).group_by(
                    col(GrantNoticeDelivery.subscriber_id),
                    col(GrantNoticeDelivery.status),
                )
            )
        ).all()
    }
    items = [
        AdminSubscriber(
            id=subscriber.id,
            email=subscriber.email,
            state=state_of(subscriber),
            consent_at=subscriber.consent_at,
            confirmed_at=subscriber.confirmed_at,
            unsubscribed_at=subscriber.unsubscribed_at,
            created_at=subscriber.created_at,
            sent=deliveries.get((subscriber.id, GrantNoticeStatus.SENT), 0),
            failed=deliveries.get((subscriber.id, GrantNoticeStatus.FAILED), 0),
        )
        for subscriber in subscribers
    ]
    return SubscriberList(
        items=items,
        totals=SubscriberTotals(
            confirmed=sum(item.state == "confirmed" for item in items),
            pending=sum(item.state == "pending" for item in items),
            unsubscribed=sum(item.state == "unsubscribed" for item in items),
            failed_deliveries=sum(item.failed for item in items),
        ),
    )


async def remove(session: AsyncSession, subscriber_id: uuid.UUID) -> bool:
    subscriber = await session.get(GrantSubscriber, subscriber_id)
    if subscriber is None:
        return False
    if subscriber.unsubscribed_at is None:
        subscriber.unsubscribed_at = datetime.now(UTC)
        session.add(subscriber)
    return True
