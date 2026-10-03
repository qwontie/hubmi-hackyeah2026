import uuid
from collections.abc import AsyncGenerator, Awaitable
from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from sqlmodel import col, delete

from api.errors import ApiError
from api.routers.api import expert_answers as routes
from api.routers.api.admin import experts as admin_routes
from services.bus import bus
from services.experts import AnswerIn, ForwardBody, by_email
from services.mail import Mailer
from services.mail.templates import StaffItemKind
from services.mail.watch import staff_item
from utils.db import session_scope
from utils.db.models import AdminAction, AdminRole, AdminUser, Need, NeedOrigin
from utils.env import MailSettings


def test_token_opens_only_its_assignment() -> None:
    first, second = uuid.uuid4(), uuid.uuid4()
    token = by_email.answer_token(first)
    assert by_email.token_opens(first, token)
    assert not by_email.token_opens(second, token)
    assert not by_email.token_opens(first, None)
    assert by_email.answer_url(first).endswith(f"/ekspert/{first}#token={token}")


@pytest.fixture
async def case(database: None) -> AsyncGenerator[tuple[Need, AdminUser, Mailer]]:
    del database
    tag = uuid.uuid4().hex[:10]
    async with session_scope() as session, httpx.AsyncClient() as client:
        need = Need(
            text=f"Brakuje opieki wytchnieniowej w gminie {tag}",
            origin=NeedOrigin.FORM,
            edit_token_hash=uuid.uuid4().hex,
        )
        admin = AdminUser(
            login=f"test-admin-{tag}",
            password_hash="x",  # noqa: S106
            role=AdminRole.ADMIN,
        )
        session.add(need)
        session.add(admin)
        await session.commit()
        await session.refresh(need)
        await session.refresh(admin)
        yield need, admin, Mailer(MailSettings(resend_api_key=SecretStr("")), client)
        await session.exec(delete(Need).where(col(Need.id) == need.id))
        await session.exec(
            delete(AdminAction).where(col(AdminAction.admin_id) == admin.id)
        )
        await session.exec(delete(AdminUser).where(col(AdminUser.id) == admin.id))
        await session.commit()


async def code_of(call: Awaitable[Any]) -> tuple[int, str]:
    with pytest.raises(ApiError) as caught:
        await call
    return caught.value.status_code, caught.value.code


async def test_forward_and_answer_by_link(case: tuple[Need, AdminUser, Mailer]) -> None:
    need, admin, mailer = case
    body = ForwardBody(
        email="Ekspertka@Example.org",
        name="Anna Kowalska",
        expertise="Usługi opiekuńcze",
        note="Czy da się to zrobić w małej gminie?",
    )
    async with session_scope() as session:
        assignment = await admin_routes.forward_need(
            need.id, body, admin, session, mailer
        )
        assert assignment.expert.id is None
        assert assignment.expert.email == "Ekspertka@example.org"
        assert assignment.delivery_status == "skipped"
        assert await code_of(
            admin_routes.forward_need(need.id, body, admin, session, mailer)
        ) == (409, "conflict")
        assert await code_of(routes.answer_view(assignment.id, session, "zly")) == (
            404,
            "not_found",
        )

        token = by_email.answer_token(assignment.id)
        for wrong in (None, "", by_email.answer_token(uuid.uuid4())):
            assert await code_of(routes.answer_view(assignment.id, session, wrong)) == (
                404,
                "not_found",
            )
            assert await code_of(
                routes.post_answer(
                    assignment.id,
                    AnswerIn(body="Odpowiedź bez właściwego klucza."),
                    session,
                    wrong,
                )
            ) == (404, "not_found")
        view = await routes.answer_view(assignment.id, session, token)
        assert view.status.value == "open"
        assert view.note == "Czy da się to zrobić w małej gminie?"
        assert view.expert.email is None
        assert view.answers == []

        async with bus.subscribe() as queue:
            answered = await routes.post_answer(
                assignment.id,
                AnswerIn(body="Tak, najlepiej razem z sąsiednią gminą i GOPS."),
                session,
                token,
            )
            event = queue.get_nowait()
        assert answered.status.value == "answered"
        assert [a.body for a in answered.answers] == [
            "Tak, najlepiej razem z sąsiednią gminą i GOPS."
        ]
        item = staff_item(event)
        assert item is not None
        assert item.kind == StaffItemKind.EXPERT_ANSWER

        notes = await admin_routes.need_assignments(need.id, session)
        assert [n.body for n in notes[0].private_notes] == [answered.answers[0].body]

        assert await code_of(
            routes.post_answer(
                assignment.id, AnswerIn(body="ok", website=""), session, token
            )
        ) == (422, "text_too_short")
        resent = await admin_routes.resend(assignment.id, admin, session, mailer)
        assert resent.delivery_status == "skipped"

        await admin_routes.unassign(assignment.id, admin, session)
        assert await code_of(routes.answer_view(assignment.id, session, token)) == (
            404,
            "not_found",
        )


async def test_double_click_on_forward_is_a_conflict(
    case: tuple[Need, AdminUser, Mailer], monkeypatch: pytest.MonkeyPatch
) -> None:
    need, admin, mailer = case
    body = ForwardBody(email="podwojny@example.org")
    async with session_scope() as session:
        first = await admin_routes.forward_need(need.id, body, admin, session, mailer)
        real = session.exec

        async def blind(statement: Any, *args: Any, **kwargs: Any) -> Any:
            result = await real(statement, *args, **kwargs)
            if "expert_email" in str(statement) and "SELECT" in str(statement):
                return EmptyResult()
            return result

        monkeypatch.setattr(session, "exec", blind)
        assert await code_of(
            admin_routes.forward_need(need.id, body, admin, session, mailer)
        ) == (409, "conflict")
        monkeypatch.undo()
        notes = await admin_routes.need_assignments(need.id, session)
        assert [a.id for a in notes] == [first.id]


class EmptyResult:
    def first(self) -> None:
        return None
