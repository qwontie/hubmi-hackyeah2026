import uuid
from datetime import timedelta
from typing import Any

import pytest

from api.errors import ApiError
from api.limits import PersistentRateLimiter, Rule
from services.ai import AiBudgetExceededError, AiUnavailableError
from services.bus import bus
from services.needs import create_need, enrich, search_need, service
from services.needs.tokens import token_matches
from utils.db import session_scope
from utils.db.models.innovation import EMBEDDING_DIMENSIONS
from utils.db.models.need import Need

pytestmark = pytest.mark.usefixtures("database")


def unique_text() -> str:
    return f"Sąsiad zostaje sam w domu i nikt nie pomaga {uuid.uuid4().hex}"


def vector() -> list[float]:
    return [1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1)


async def model_down(*_: Any, **__: Any) -> Any:
    raise AiUnavailableError


async def budget_spent(*_: Any, **__: Any) -> Any:
    raise AiBudgetExceededError


@pytest.fixture
def no_background(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    scheduled: list[uuid.UUID] = []
    monkeypatch.setattr(service, "schedule_enrichment", scheduled.append)
    monkeypatch.setattr(service, "schedule_summary", lambda _: None)
    monkeypatch.setattr(enrich, "schedule_summary", lambda _: None)
    return scheduled


async def test_need_is_stored_at_once_when_the_model_is_down(
    monkeypatch: pytest.MonkeyPatch,
    created_needs: list[uuid.UUID],
    no_background: list[uuid.UUID],
) -> None:
    monkeypatch.setattr(enrich, "embed_query", model_down)
    monkeypatch.setattr(enrich, "run_agent", model_down)
    text = unique_text()
    async with bus.subscribe() as queue, session_scope() as session:
        outcome = await create_need(
            session, text, powiat=None, contact_email=None, client="10.0.0.1"
        )
        created_needs.append(outcome.need.id)
        message = queue.get_nowait()
    assert message.topic == "need.created"
    assert message.data["id"] == str(outcome.need.id)
    assert outcome.need.text == text
    assert outcome.need.title == "Sąsiad zostaje sam w domu i nikt nie…"
    assert outcome.need.embedding is None
    assert outcome.cluster is None
    assert no_background == [outcome.need.id]
    assert await enrich.enrich_need(outcome.need.id) is False
    async with session_scope() as session:
        stored = await session.get(Need, outcome.need.id)
        assert stored is not None
        assert stored.embedding is None


async def test_spent_budget_does_not_block_registration(
    monkeypatch: pytest.MonkeyPatch,
    created_needs: list[uuid.UUID],
    no_background: list[uuid.UUID],
) -> None:
    monkeypatch.setattr(enrich, "embed_query", budget_spent)
    async with session_scope() as session:
        outcome = await create_need(
            session, unique_text(), powiat=None, contact_email=None
        )
        created_needs.append(outcome.need.id)
    assert outcome.need.number
    assert no_background == [outcome.need.id]
    assert await enrich.enrich_need(outcome.need.id) is False


async def test_need_is_enriched_later_when_the_model_is_back(
    created_needs: list[uuid.UUID], fake_ai: dict[str, str]
) -> None:
    async with session_scope() as session:
        outcome = await create_need(
            session, unique_text(), powiat=None, contact_email=None
        )
        created_needs.append(outcome.need.id)
    fake_ai["Sąsiad zostaje sam"] = "Samotność starszego sąsiada"
    async with bus.subscribe() as queue:
        assert await enrich.enrich_need(outcome.need.id) is True
        message = queue.get_nowait()
    assert message.topic == "need.updated"
    assert message.data["title"] == "Samotność starszego sąsiada"
    assert message.data["cluster"] is not None
    async with session_scope() as session:
        stored = await session.get(Need, outcome.need.id)
        assert stored is not None
        assert stored.embedding is not None
        assert stored.cluster_id is not None


async def test_same_text_from_same_client_returns_the_existing_need(
    created_needs: list[uuid.UUID], no_background: list[uuid.UUID]
) -> None:
    text = unique_text()
    async with session_scope() as session:
        first = await create_need(
            session, text, powiat=None, contact_email=None, client="10.0.0.2"
        )
        created_needs.append(first.need.id)
    async with session_scope() as session:
        again = await create_need(
            session,
            f"  {text.upper()} ",
            powiat=None,
            contact_email="drugi@hubmi.test",
            client="10.0.0.2",
        )
    async with session_scope() as session:
        other = await create_need(
            session, text, powiat=None, contact_email=None, client="10.0.0.3"
        )
        created_needs.append(other.need.id)
    assert again.duplicate is True
    assert again.need.id == first.need.id
    assert again.token == first.token
    async with session_scope() as session:
        stored = await session.get(Need, first.need.id)
        assert stored is not None
        assert token_matches(first.token, stored.edit_token_hash)
        assert stored.contact_email == "drugi@hubmi.test"
    assert other.duplicate is False
    assert other.need.id != first.need.id
    assert no_background == [first.need.id, other.need.id]


async def test_match_answers_without_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "cached_query_embedding", model_down)
    monkeypatch.setattr(service, "decide", model_down)
    async with session_scope() as session:
        outcome = await search_need(session, "Nie ma kto zająć się babcią po pracy")
    assert outcome.degraded is True
    assert outcome.reason in {None, "no_match"}
    assert bool(outcome.results) == (outcome.reason is None)


async def test_match_answers_unclear_text_without_calling_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "cached_query_embedding", model_down)
    async with session_scope() as session:
        outcome = await search_need(session, "?!?! 1234")
    assert outcome.results == []
    assert outcome.reason == "unclear"
    assert outcome.degraded is False


async def test_persistent_rate_limit_counts_in_postgres() -> None:
    limiter = PersistentRateLimiter(f"test-{uuid.uuid4().hex}", Rule(2, 60))
    await limiter.check("10.0.0.9")
    await limiter.check("10.0.0.9")
    with pytest.raises(ApiError) as caught:
        await limiter.check("10.0.0.9")
    assert caught.value.status_code == 429
    assert caught.value.code == "rate_limited"
    await limiter.check("10.0.0.10")


async def test_duplicate_never_overwrites_the_first_contact(
    created_needs: list[uuid.UUID], no_background: list[uuid.UUID]
) -> None:
    text = unique_text()
    async with session_scope() as session:
        first = await create_need(
            session,
            text,
            powiat=None,
            contact_email="pierwszy@hubmi.test",
            client="10.0.0.4",
        )
        created_needs.append(first.need.id)
    async with session_scope() as session:
        again = await create_need(
            session,
            text,
            powiat=None,
            contact_email="drugi@hubmi.test",
            client="10.0.0.4",
        )
    assert again.duplicate is True
    assert no_background == [first.need.id]
    async with session_scope() as session:
        stored = await session.get(Need, first.need.id)
        assert stored is not None
        assert stored.contact_email == "pierwszy@hubmi.test"


@pytest.mark.usefixtures("fake_ai")
async def test_no_group_is_named_with_the_residents_own_words(
    monkeypatch: pytest.MonkeyPatch, created_needs: list[uuid.UUID]
) -> None:
    async with session_scope() as session:
        outcome = await create_need(
            session, unique_text(), powiat=None, contact_email=None
        )
        created_needs.append(outcome.need.id)
    monkeypatch.setattr(enrich, "run_agent", model_down)
    assert await enrich.enrich_need(outcome.need.id) is None
    async with session_scope() as session:
        stored = await session.get(Need, outcome.need.id)
        assert stored is not None
        assert stored.embedding is not None
        assert stored.cluster_id is None
    monkeypatch.setattr(enrich, "SWEEP_MIN_AGE", timedelta(0))
    monkeypatch.setattr(enrich, "SWEEP_BATCH", 10_000)
    assert outcome.need.id in await enrich.pending_needs()


async def test_recipient_cap_allows_two_letters_a_day() -> None:
    limiter = PersistentRateLimiter(f"test-{uuid.uuid4().hex}", Rule(2, 86400))
    address = f"{uuid.uuid4().hex}@hubmi.test"
    assert await limiter.allows(address)
    assert await limiter.allows(address)
    assert not await limiter.allows(address)
