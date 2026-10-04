import hashlib
import hmac
from typing import Any

from pydantic import BaseModel
from sqlalchemy import ColumnElement, func
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.dml import Update
from sqlmodel import col, delete, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import (
    AdminUser,
    Assignment,
    ExpertNote,
    GrantApplication,
    GrantNoticeDelivery,
    GrantSubscriber,
    Idea,
    Need,
    TestSignup,
)
from utils.db.models.demand import InnovationDemand
from utils.db.models.volunteer import VolunteerMessage, VolunteerReport
from utils.env import env

from . import audit

ACTION = "contact.erase"


class EraseResult(BaseModel):
    erased: dict[str, int]
    total: int


def address_hash(email: str) -> str:
    key = env.auth.secret.get_secret_value().encode() or b"hubmi"
    return hmac.new(key, email.encode(), hashlib.sha256).hexdigest()


def same(column: Mapped[Any], email: str) -> ColumnElement[bool]:
    return func.lower(column) == email


async def changed(session: AsyncSession, statement: Update) -> int:
    result = await session.exec(statement)
    return int(result.rowcount or 0)


async def count(session: AsyncSession, column: Mapped[Any], ids: list[Any]) -> int:
    if not ids:
        return 0
    return int(
        await session.scalar(
            select(func.count(col(column))).where(col(column).in_(ids))
        )
        or 0
    )


async def ids_of(
    session: AsyncSession, column: Mapped[Any], condition: ColumnElement[bool]
) -> list[Any]:
    return list((await session.exec(select(column).where(condition))).all())


async def erase(session: AsyncSession, admin: AdminUser, email: str) -> EraseResult:
    erased: dict[str, int] = {}
    erased["need"] = await changed(
        session,
        update(Need)
        .where(same(col(Need.contact_email), email))
        .values(contact_email=None, contact_consent=False, consent_at=None),
    )
    erased["idea"] = await changed(
        session,
        update(Idea)
        .where(same(col(Idea.contact_email), email))
        .values(contact_email=None, contact_consent=False, consent_at=None),
    )
    erased["grant_application"] = await changed(
        session,
        update(GrantApplication)
        .where(same(col(GrantApplication.contact_email), email))
        .values(contact_email=None, contact_consent=False),
    )
    erased["innovation_demand"] = await changed(
        session,
        update(InnovationDemand)
        .where(same(col(InnovationDemand.contact_email), email))
        .values(contact_email=None, consent_at=None),
    )
    signups = await ids_of(
        session, col(TestSignup.id), same(col(TestSignup.contact_email), email)
    )
    erased["test_signup"] = len(signups)
    erased["volunteer_message"] = await count(
        session, col(VolunteerMessage.signup_id), signups
    )
    erased["volunteer_report"] = await count(
        session, col(VolunteerReport.signup_id), signups
    )
    if signups:
        await session.exec(delete(TestSignup).where(col(TestSignup.id).in_(signups)))
    assignments = await ids_of(
        session, col(Assignment.id), same(col(Assignment.expert_email), email)
    )
    erased["assignment"] = len(assignments)
    erased["expert_note"] = await count(
        session, col(ExpertNote.assignment_id), assignments
    )
    if assignments:
        await session.exec(
            delete(Assignment).where(col(Assignment.id).in_(assignments))
        )
    subscribers = await ids_of(
        session, col(GrantSubscriber.id), same(col(GrantSubscriber.email), email)
    )
    erased["grant_subscriber"] = len(subscribers)
    erased["grant_notice_delivery"] = await count(
        session, col(GrantNoticeDelivery.subscriber_id), subscribers
    )
    if subscribers:
        await session.exec(
            delete(GrantSubscriber).where(col(GrantSubscriber.id).in_(subscribers))
        )
    total = sum(erased.values())
    digest = address_hash(email)
    audit.record(
        session,
        admin,
        ACTION,
        target=("contact", digest[:16]),
        details={"address_hash": digest, "erased": erased, "total": total},
    )
    await session.commit()
    return EraseResult(erased=erased, total=total)
