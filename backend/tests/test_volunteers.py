import uuid
from collections.abc import AsyncGenerator, Awaitable
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from fastapi import Response
from pydantic import SecretStr
from sqlmodel import col, delete

from api.errors import ApiError
from api.routers.api.modules import volunteers as routes
from services.bus import bus
from services.mail import Mailer
from services.mail.templates import StaffItemKind
from services.mail.watch import staff_item
from services.tester import volunteers
from services.tester.schemas import AcceptIn, RejectIn, ReportIn, VolunteerIn
from services.tester.volunteers import Action, InvalidTransitionError, next_status
from utils.db import session_scope
from utils.db.models import AdminAction, AdminRole, AdminUser, Category, Innovation
from utils.db.models.innovation import InnovationStatus
from utils.db.models.test_signup import SignupStatus, TestSignup
from utils.db.models.volunteer import Recommendation, VolunteerMessage
from utils.env import MailSettings

S = SignupStatus


@pytest.mark.parametrize(
    ("current", "action", "expected"),
    [
        (S.NEW, Action.ACCEPT, S.ACCEPTED),
        (S.NEW, Action.REJECT, S.REJECTED),
        (S.ACCEPTED, Action.REPORT, S.REPORTED),
        (S.REPORTED, Action.REPORT, S.REPORTED),
        (S.ACCEPTED, Action.CLOSE, S.CLOSED),
        (S.REPORTED, Action.CLOSE, S.CLOSED),
    ],
)
def test_allowed_moves(current: S, action: Action, expected: S) -> None:
    assert next_status(current, action) == expected


@pytest.mark.parametrize(
    ("current", "action"),
    [
        (S.NEW, Action.REPORT),
        (S.NEW, Action.CLOSE),
        (S.ACCEPTED, Action.ACCEPT),
        (S.ACCEPTED, Action.REJECT),
        (S.REPORTED, Action.REJECT),
        (S.REJECTED, Action.ACCEPT),
        (S.REJECTED, Action.REPORT),
        (S.REJECTED, Action.CLOSE),
        (S.CLOSED, Action.REPORT),
        (S.CLOSED, Action.ACCEPT),
        (S.CLOSED, Action.CLOSE),
    ],
)
def test_forbidden_moves(current: S, action: Action) -> None:
    with pytest.raises(InvalidTransitionError):
        next_status(current, action)


def test_token_belongs_to_one_application() -> None:
    first, second = uuid.uuid4(), uuid.uuid4()
    token = volunteers.report_token(first)
    assert token
    assert volunteers.token_opens(first, token)
    assert not volunteers.token_opens(second, token)
    assert not volunteers.token_opens(first, None)
    assert not volunteers.token_opens(first, token[:-1] + "x")
    assert volunteers.report_url(first).endswith(f"/wolontariat/{first}#token={token}")


@dataclass
class World:
    innovation: Innovation
    admin: AdminUser
    mailer: Mailer


@pytest.fixture
async def world(database: None) -> AsyncGenerator[World]:
    del database
    tag = uuid.uuid4().hex[:10]
    async with session_scope() as session, httpx.AsyncClient() as client:
        category = Category(
            slug=f"test-cat-{tag}", name="Test", source_url="https://rops.krakow.pl"
        )
        innovation = Innovation(
            slug=f"test-inno-{tag}",
            category_slug=category.slug,
            title="Rozwiązanie testowe",
            status=InnovationStatus.PUBLISHED,
        )
        admin = AdminUser(
            login=f"test-admin-{tag}",
            password_hash="x",  # noqa: S106
            role=AdminRole.ADMIN,
        )
        session.add(category)
        await session.flush()
        session.add(innovation)
        session.add(admin)
        await session.commit()
        await session.refresh(innovation)
        await session.refresh(admin)
        mailer = Mailer(MailSettings(resend_api_key=SecretStr("")), client)
        yield World(innovation=innovation, admin=admin, mailer=mailer)
        await session.exec(
            delete(Innovation).where(col(Innovation.id) == innovation.id)
        )
        await session.exec(delete(Category).where(col(Category.slug) == category.slug))
        await session.exec(
            delete(AdminAction).where(col(AdminAction.admin_id) == admin.id)
        )
        await session.exec(delete(AdminUser).where(col(AdminUser.id) == admin.id))
        await session.commit()


def application(email: str = "wolontariusz@example.org") -> VolunteerIn:
    return VolunteerIn(
        email=email,
        contact_consent=True,
        powiat="powiat-limanowski",
        who="ngo",
        proposal="Chcemy sprawdzić to rozwiązanie z grupą seniorów w naszym klubie.",
    )


def report(activity: str = "Dwa spotkania w klubie seniora z opiekunkami.") -> ReportIn:
    return ReportIn(
        activity=activity,
        participants=14,
        worked="Rozmowy w małych grupach",
        not_worked="nic",
        recommend=Recommendation.AFTER_CHANGES,
    )


async def code_of(call: Awaitable[Any]) -> tuple[int, str]:
    with pytest.raises(ApiError) as caught:
        await call
    return caught.value.status_code, caught.value.code


async def test_full_flow_through_the_token_form(world: World) -> None:
    async with session_scope() as session:
        created = await routes.apply(
            world.innovation.slug, application(), Response(), session, world.mailer
        )
        assert not created.duplicate
        again = await routes.apply(
            world.innovation.slug, application(), Response(), session, world.mailer
        )
        assert again.id == created.id
        assert again.duplicate
        signup_id = created.id
        token = volunteers.report_token(signup_id)

        assert await code_of(routes.volunteer(signup_id, session, None, "zly")) == (
            404,
            "not_found",
        )
        view = await routes.volunteer(signup_id, session, None, token)
        assert view.status == S.NEW
        assert not view.editable
        assert await code_of(
            routes.put_report(signup_id, report(), session, token)
        ) == (409, "report_locked")

        detail = await routes.accept(
            signup_id, AcceptIn(), world.admin, session, world.mailer
        )
        assert detail.status == S.ACCEPTED
        assert detail.decided_at is not None
        assert [m.kind.value for m in detail.messages] == ["accept"]
        assert detail.messages[0].delivery_status.value == "skipped"
        assert await code_of(
            routes.reject(
                signup_id,
                RejectIn(reason="za późno"),
                world.admin,
                session,
                world.mailer,
            )
        ) == (409, "invalid_transition")

        async with bus.subscribe() as queue:
            first = await routes.put_report(signup_id, report(), session, token)
            first_event = queue.get_nowait()
            second = await routes.put_report(
                signup_id,
                report("Trzy spotkania w klubie seniora z opiekunkami."),
                session,
                token,
            )
            second_event = queue.get_nowait()
        assert first.status == S.REPORTED
        assert first.editable
        assert second.report is not None
        assert second.report.activity.startswith("Trzy")
        first_item = staff_item(first_event)
        assert first_item is not None
        assert first_item.kind == StaffItemKind.VOLUNTEER_REPORT
        assert staff_item(second_event) is None

        closed = await routes.close(signup_id, world.admin, session)
        assert closed.status == S.CLOSED
        assert await code_of(
            routes.put_report(signup_id, report(), session, token)
        ) == (409, "report_locked")
        locked = await routes.volunteer(signup_id, session, None, token)
        assert not locked.editable
        assert locked.report is not None


async def test_reject_fills_the_reason_into_the_letter(world: World) -> None:
    async with session_scope() as session:
        created = await routes.apply(
            world.innovation.slug,
            application("inny@example.org"),
            Response(),
            session,
            world.mailer,
        )
        detail = await routes.reject(
            created.id,
            RejectIn(reason="Szukamy teraz grup z powiatu nowotarskiego."),
            world.admin,
            session,
            world.mailer,
        )
        assert detail.status == S.REJECTED
        assert detail.decision_reason == "Szukamy teraz grup z powiatu nowotarskiego."
        assert "{reason}" not in detail.messages[0].body
        assert "powiatu nowotarskiego" in detail.messages[0].body
        retry = await routes.apply(
            world.innovation.slug,
            application("inny@example.org"),
            Response(),
            session,
            world.mailer,
        )
        assert not retry.duplicate
        await session.exec(
            delete(VolunteerMessage).where(
                col(VolunteerMessage.signup_id).in_([created.id, retry.id])
            )
        )
        await session.exec(
            delete(TestSignup).where(col(TestSignup.id).in_([created.id, retry.id]))
        )
        await session.commit()


async def test_honeypot_and_short_proposal_are_rejected(world: World) -> None:
    async with session_scope() as session:
        trap = application()
        trap.website = "https://spam.example"
        assert await code_of(
            routes.apply(world.innovation.slug, trap, Response(), session, world.mailer)
        ) == (422, "spam_rejected")
        short = application()
        short.proposal = "za krótko"
        assert await code_of(
            routes.apply(
                world.innovation.slug, short, Response(), session, world.mailer
            )
        ) == (422, "text_too_short")
