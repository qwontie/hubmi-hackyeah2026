import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from services.needs import create_need, service
from services.replies import ReplySuggestions, cached, suggest
from services.replies import service as replies
from utils.db import session_scope
from utils.db.models.need import Need

pytestmark = pytest.mark.usefixtures("database")


async def test_suggestions_are_generated_once_per_need(
    monkeypatch: pytest.MonkeyPatch, created_needs: list[uuid.UUID]
) -> None:
    monkeypatch.setattr(service, "schedule_enrichment", lambda _: None)
    calls: list[uuid.UUID] = []

    async def generate(_: Any, need: Need) -> ReplySuggestions:
        calls.append(need.id)
        return ReplySuggestions(
            fragments=[], earlier_answers=[], generated_at=datetime.now(UTC)
        )

    monkeypatch.setattr(replies, "_generate", generate)
    async with session_scope() as session:
        outcome = await create_need(
            session,
            f"Brakuje opieki wytchnieniowej w gminie {uuid.uuid4().hex}",
            powiat=None,
            contact_email=None,
        )
        created_needs.append(outcome.need.id)
    async with session_scope() as session:
        need = await session.get(Need, outcome.need.id)
        assert need is not None
        assert cached(need) is None
        first = await suggest(session, need)
    async with session_scope() as session:
        need = await session.get(Need, outcome.need.id)
        assert need is not None
        assert cached(need) == first
        assert await suggest(session, need) == first
        assert len(calls) == 1
        renewed = await suggest(session, need, refresh=True)
    assert len(calls) == 2
    assert renewed.generated_at > first.generated_at
