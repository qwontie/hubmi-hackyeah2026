import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlmodel import col, delete

from services.dialogue import service as dialogue
from services.grants import applications
from services.grants.templates import TEMPLATES
from services.mail import Delivery, DeliveryStatus, Email, Mailer
from utils.db import session_scope
from utils.db.models import (
    AdminUser,
    GrantApplication,
    GrantCall,
    GrantCallStatus,
    Message,
    MessageDelivery,
)

pytestmark = pytest.mark.usefixtures("database")


class FakeMailer(Mailer):
    def __init__(self) -> None:
        self.sent: list[Email] = []

    async def send(self, email: Email) -> Delivery:
        self.sent.append(email)
        return Delivery(DeliveryStatus.SENT, provider_id="fake")


@pytest.fixture
async def setup() -> AsyncGenerator[tuple[GrantCall, AdminUser]]:
    template = next(iter(TEMPLATES.values()))
    now = datetime.now(UTC)
    call = GrantCall(
        title=f"Nabór testowy {uuid.uuid4().hex}",
        description="Opis.",
        opens_at=now - timedelta(days=1),
        closes_at=now + timedelta(days=7),
        status=GrantCallStatus.PUBLISHED,
        sections=[s.model_dump() for s in template.sections],
    )
    admin = AdminUser(
        login=f"test-{uuid.uuid4().hex[:8]}", password_hash=uuid.uuid4().hex
    )
    async with session_scope() as session:
        session.add(call)
        session.add(admin)
        await session.commit()
        await session.refresh(call)
        await session.refresh(admin)
    yield call, admin
    async with session_scope() as session:
        await session.exec(
            delete(GrantApplication).where(col(GrantApplication.call_id) == call.id)
        )
        await session.exec(delete(GrantCall).where(col(GrantCall.id) == call.id))
        await session.exec(delete(AdminUser).where(col(AdminUser.id) == admin.id))
        await session.commit()


async def test_staff_reply_reaches_the_author_of_an_application_without_idea(
    monkeypatch: pytest.MonkeyPatch, setup: tuple[GrantCall, AdminUser]
) -> None:
    call, admin = setup
    spawned: list[Any] = []
    monkeypatch.setattr(dialogue, "spawn", spawned.append)
    mailer = FakeMailer()
    async with session_scope() as session:
        application, _, _ = await applications.start(session, call, None)
        applications.set_contact(application, email="autor@hubmi.test", consent=True)
        session.add(application)
        await session.commit()
        sent = await dialogue.reply(
            session, application, admin, "Dziękujemy za wniosek.", mailer
        )
    assert sent.application_id == application.id
    assert sent.need_id is None
    assert sent.idea_id is None
    assert sent.delivery_status == MessageDelivery.PENDING
    for job in spawned:
        job.close()
    await dialogue.deliver(sent.id, mailer)
    assert len(mailer.sent) == 1
    assert mailer.sent[0].to == "autor@hubmi.test"
    assert f"nr {application.number}" in mailer.sent[0].text
    assert call.title in mailer.sent[0].text
    async with session_scope() as session:
        thread = await dialogue.thread_for_admin(session, application)
        stored = await session.get(Message, sent.id)
    assert [m.id for m in thread] == [sent.id]
    assert stored is not None
    assert stored.delivery_status == MessageDelivery.SENT


async def test_reply_without_contact_is_kept_but_not_mailed(
    monkeypatch: pytest.MonkeyPatch, setup: tuple[GrantCall, AdminUser]
) -> None:
    call, admin = setup
    monkeypatch.setattr(dialogue, "spawn", lambda job: job.close())
    async with session_scope() as session:
        application, _, _ = await applications.start(session, call, None)
        sent = await dialogue.reply(
            session, application, admin, "Dziękujemy.", FakeMailer()
        )
    assert sent.delivery_status is None
