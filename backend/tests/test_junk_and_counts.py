import uuid
from typing import Any

import pytest
from sqlmodel import col, delete

from api.routers.api.public.match import log_search
from services.dialogue import inbox
from services.needs import attach_need, clusters, create_need, detach_need, enrich
from services.needs.service import SearchOutcome
from services.stats.queries import collect
from services.stats.schemas import Period
from utils.db import session_scope
from utils.db.models import SearchLog
from utils.db.models.innovation import EMBEDDING_DIMENSIONS
from utils.db.models.need import Need, NeedCluster, NeedStatus

pytestmark = pytest.mark.usefixtures("database")


def lonely_vector() -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[uuid.uuid4().int % (EMBEDDING_DIMENSIONS - 1) + 1] = 1.0
    return vector


async def registered(
    created_needs: list[uuid.UUID],
    vector: list[float],
    fake_ai: dict[str, str],
    title: str | None = None,
) -> Need:
    marker = uuid.uuid4().hex
    fake_ai[marker] = title or f"Zakupy dla sąsiadki {marker}"
    async with session_scope() as session:
        outcome = await create_need(
            session,
            f"Nie ma kto pomóc sąsiadce w zakupach {marker}",
            powiat=None,
            contact_email=None,
            vector=vector,
        )
    created_needs.append(outcome.need.id)
    assert outcome.cluster is None
    assert await enrich.enrich_need(outcome.need.id) is True
    async with session_scope() as session:
        need = await session.get(Need, outcome.need.id)
    assert need is not None
    return need


async def test_same_problem_shares_a_group_other_problems_do_not(
    created_needs: list[uuid.UUID], fake_ai: dict[str, str]
) -> None:
    title = f"Brak pomocy w zakupach {uuid.uuid4().hex}"
    first = await registered(created_needs, lonely_vector(), fake_ai, title)
    second = await registered(created_needs, lonely_vector(), fake_ai, title)
    other = await registered(created_needs, lonely_vector(), fake_ai)
    assert first.cluster_id is not None
    assert second.cluster_id == first.cluster_id
    assert other.cluster_id not in {None, first.cluster_id}


async def test_junk_leaves_the_group_and_every_count(
    created_needs: list[uuid.UUID], fake_ai: dict[str, str]
) -> None:
    vector = lonely_vector()
    need = await registered(created_needs, vector, fake_ai)
    assert need.cluster_id is not None
    cluster_id = need.cluster_id
    async with session_scope() as session:
        before = await inbox.counts(session)
        waiting_before = (await collect(session, Period.WEEK, {})).totals.waiting
        stored = await session.get(Need, need.id)
        assert stored is not None
        stored.status = NeedStatus.JUNK
        assert await detach_need(session, stored) is None
        await session.commit()
        assert await session.get(NeedCluster, cluster_id) is None
        after = await inbox.counts(session)
        stats = await collect(session, Period.WEEK, {})
        assert await clusters.similar_count(session, vector) == 0
    assert after["junk"] == before["junk"] + 1
    assert after["waiting"] == before["waiting"] - 1
    assert after["total"] == before["total"] - 1
    assert stats.totals.waiting == waiting_before - 1
    assert stats.totals.waiting == after["waiting"]
    async with session_scope() as session:
        stored = await session.get(Need, need.id)
        assert stored is not None
        stored.status = NeedStatus.NEW
        back = await attach_need(session, stored)
        await session.commit()
        assert back is not None
        assert stored.cluster_id == back.id
        assert await clusters.similar_count(session, vector) == 1


async def test_staff_title_survives_the_summary(
    monkeypatch: pytest.MonkeyPatch,
    created_needs: list[uuid.UUID],
    fake_ai: dict[str, str],
) -> None:
    need = await registered(created_needs, lonely_vector(), fake_ai)
    assert need.cluster_id is not None

    async def summarized(*_: Any, **__: Any) -> clusters.ClusterSummary:
        return clusters.ClusterSummary(title="Tytuł od modelu", summary="Opis.")

    monkeypatch.setattr(clusters, "run_agent", summarized)
    async with session_scope() as session:
        cluster = await session.get(NeedCluster, need.cluster_id)
        assert cluster is not None
        cluster.title = "Zakupy dla sąsiadów"
        cluster.title_locked = True
        session.add(cluster)
        await session.commit()
    refreshed = await clusters.refresh_cluster_summary(need.cluster_id)
    assert refreshed is not None
    assert refreshed.title == "Zakupy dla sąsiadów"
    assert refreshed.summary == "Opis."


async def test_search_log_keeps_no_text() -> None:
    outcome = SearchOutcome([], 0, None, degraded=True, reason="no_match")
    await log_search(outcome)
    async with session_scope() as session:
        stats = await collect(session, Period.WEEK, {})
        assert stats.searches.no_match >= 1
        assert stats.searches.degraded >= 1
        assert set(SearchLog.model_fields) == {
            "id",
            "outcome",
            "category_slug",
            "slugs",
            "scores",
            "degraded",
            "created_at",
        }
        await session.exec(
            delete(SearchLog).where(
                col(SearchLog.outcome) == "no_match",
                col(SearchLog.degraded).is_(True),
                col(SearchLog.slugs) == [],
            )
        )
        await session.commit()
