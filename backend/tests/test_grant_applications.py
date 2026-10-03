import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlmodel import col, delete

from services.ai import AiUnavailableError
from services.grants import applications, drafting
from services.grants.drafting import Draft, DraftSection
from services.grants.templates import TEMPLATES
from services.needs.tokens import new_token
from utils.db import session_scope
from utils.db.models import GrantApplication, GrantCall, GrantCallStatus, Idea
from utils.db.models.idea import IdeaStage

pytestmark = pytest.mark.usefixtures("database")


async def no_model(*_: Any, **__: Any) -> Any:
    raise AssertionError


@pytest.fixture
async def call() -> AsyncGenerator[GrantCall]:
    template = next(iter(TEMPLATES.values()))
    now = datetime.now(UTC)
    found = GrantCall(
        title=f"Nabór testowy {uuid.uuid4().hex}",
        description="Opis naboru testowego.",
        opens_at=now - timedelta(days=1),
        closes_at=now + timedelta(days=7),
        status=GrantCallStatus.PUBLISHED,
        sections=[s.model_dump() for s in template.sections],
    )
    async with session_scope() as session:
        session.add(found)
        await session.commit()
        await session.refresh(found)
    yield found
    async with session_scope() as session:
        await session.exec(
            delete(GrantApplication).where(col(GrantApplication.call_id) == found.id)
        )
        await session.exec(delete(GrantCall).where(col(GrantCall.id) == found.id))
        await session.commit()


@pytest.fixture
async def idea() -> AsyncGenerator[Idea]:
    _, token_hash = new_token()
    found = Idea(
        title="Wspólne zakupy sąsiedzkie",
        essence="Sąsiedzi robią zakupy dla osób starszych z bloku.",
        for_whom="Osoby starsze mieszkające same",
        stage=IdeaStage.IDEA,
        canvas={"problem": "Seniorzy nie mają jak zrobić zakupów.", "partners": ""},
        edit_token_hash=token_hash,
    )
    async with session_scope() as session:
        session.add(found)
        await session.commit()
        await session.refresh(found)
    yield found
    async with session_scope() as session:
        await session.exec(delete(Idea).where(col(Idea.id) == found.id))
        await session.commit()


async def test_application_without_idea_starts_empty_without_a_model(
    monkeypatch: pytest.MonkeyPatch, call: GrantCall
) -> None:
    monkeypatch.setattr(drafting, "run_agent", no_model)
    async with session_scope() as session:
        application, token, created = await applications.start(session, call, None)
        out = applications.view(application, call, None)
    assert created is True
    assert out.idea is None
    assert {s.source for s in out.sections} == {"empty"}
    assert set(out.missing_required) == {s.key for s in out.sections if s.required}
    assert applications.token_opens_application(application, token)
    assert not applications.token_opens_application(application, token + "x")


async def test_idea_answers_are_copied_plainly_and_reused(
    monkeypatch: pytest.MonkeyPatch, call: GrantCall, idea: Idea
) -> None:
    monkeypatch.setattr(drafting, "run_agent", no_model)
    async with session_scope() as session:
        first, first_token, created = await applications.start(session, call, idea)
        out = applications.view(first, call, idea)
    by_key = {s.key: s for s in out.sections}
    assert created is True
    assert by_key["title"].text == idea.title
    assert by_key["title"].source == "idea"
    assert by_key["description"].text == idea.essence
    assert by_key["recipients"].text == idea.for_whom
    assert by_key["diagnosis"].text == "Seniorzy nie mają jak zrobić zakupów."
    assert by_key["team"].source == "empty"
    async with session_scope() as session:
        again, again_token, created_again = await applications.start(
            session, call, idea
        )
    assert created_again is False
    assert again.id == first.id
    assert applications.token_opens_application(again, again_token)
    assert not applications.token_opens_application(again, first_token)


async def test_suggestion_fills_only_what_the_author_did_not_write(
    monkeypatch: pytest.MonkeyPatch, call: GrantCall
) -> None:
    seen: list[str] = []

    async def drafted(_: Any, prompt: str, **__: Any) -> Draft:
        seen.append(prompt)
        return Draft(
            sections=[
                DraftSection(key=s["key"], text=f"Propozycja {s['key']}")
                for s in call.sections
            ]
        )

    monkeypatch.setattr(drafting, "run_agent", drafted)
    async with session_scope() as session:
        application, _, _ = await applications.start(session, call, None)
        with pytest.raises(applications.NothingToDraftError):
            await applications.suggest(session, application, call, None, None)
        assert seen == []
        applications.edit_sections(application, call, {"title": "Mój tytuł"})
        session.add(application)
        await session.commit()
        application = await applications.suggest(session, application, call, None, None)
        out = applications.view(application, call, None)
    by_key = {s.key: s for s in out.sections}
    assert "Mój tytuł" in seen[0]
    assert by_key["title"].text == "Mój tytuł"
    assert by_key["title"].source == "author"
    assert by_key["description"].source == "ai"
    assert out.missing_required == []


async def test_submit_needs_only_filled_required_sections(call: GrantCall) -> None:
    async with session_scope() as session:
        application, _, _ = await applications.start(session, call, None)
        errors = applications.submit_errors(application, call)
    required = {f"sections.{s['key']}" for s in call.sections if s["required"]}
    assert {e["field"] for e in errors} == required


async def test_model_down_leaves_the_application_as_it_was(
    monkeypatch: pytest.MonkeyPatch, call: GrantCall, idea: Idea
) -> None:
    async def down(*_: Any, **__: Any) -> Any:
        raise AiUnavailableError

    monkeypatch.setattr(drafting, "run_agent", down)
    async with session_scope() as session:
        application, _, _ = await applications.start(session, call, idea)
        before = dict(application.sections)
        with pytest.raises(AiUnavailableError):
            await applications.suggest(session, application, call, idea, None)
        await session.refresh(application)
        assert application.sections == before


async def test_unedited_ai_placeholder_blocks_submit(
    monkeypatch: pytest.MonkeyPatch, call: GrantCall, idea: Idea
) -> None:
    async def drafted(*_: Any, **__: Any) -> Draft:
        return Draft(
            sections=[
                DraftSection(
                    key=s["key"],
                    text="Pomysł nie opisuje jeszcze tej części.",
                    missing=["koszty"],
                )
                for s in call.sections
            ]
        )

    monkeypatch.setattr(drafting, "run_agent", drafted)
    async with session_scope() as session:
        application, _, _ = await applications.start(session, call, idea)
        application = await applications.suggest(
            session, application, call, idea, ["team"]
        )
        out = applications.view(application, call, idea)
        errors = applications.submit_errors(application, call)
    by_key = {s.key: s for s in out.sections}
    assert by_key["team"].source == "ai"
    assert by_key["title"].source == "idea"
    required_team = next(s for s in call.sections if s["key"] == "team")["required"]
    assert ("team" in out.missing_required) == required_team
    assert ("sections.team" in {e["field"] for e in errors}) == required_team
    assert "title" not in out.missing_required
