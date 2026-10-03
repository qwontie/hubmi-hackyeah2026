import hashlib
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy import text
from sqlmodel import col, delete, select

from services.needs import clusters, enrich, service
from utils.db import session_scope
from utils.db.models.innovation import EMBEDDING_DIMENSIONS
from utils.db.models.need import Need, NeedCluster


@pytest.fixture(scope="session")
async def database() -> None:
    try:
        async with session_scope() as session:
            await session.exec(select(1))
            ready = await session.scalar(text("SELECT to_regclass('rate_counter')"))
    except OSError as e:
        pytest.skip(f"no test database: {e}")
    if ready is None:
        pytest.skip("test database is not migrated to head")


@pytest.fixture
async def created_needs(database: None) -> AsyncGenerator[list[uuid.UUID]]:
    del database
    ids: list[uuid.UUID] = []
    yield ids
    async with session_scope() as session:
        clusters = (
            await session.exec(select(Need.cluster_id).where(col(Need.id).in_(ids)))
        ).all()
        await session.exec(delete(Need).where(col(Need.id).in_(ids)))
        await session.exec(
            delete(NeedCluster).where(
                col(NeedCluster.id).in_([c for c in clusters if c is not None])
            )
        )
        await session.commit()


def one_hot(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    digest = hashlib.sha256(text.casefold().encode()).digest()
    vector[int.from_bytes(digest[:4]) % EMBEDDING_DIMENSIONS] = 1.0
    return vector


@pytest.fixture
def fake_ai(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    titles: dict[str, str] = {}

    async def embed_text(text: str, **_: Any) -> list[float]:
        return one_hot(text)

    async def embed_titles(texts: list[str], **_: Any) -> list[list[float]]:
        return [one_hot(text) for text in texts]

    async def title(agent: Any, prompt: str, **_: Any) -> Any:
        del agent
        for key, value in titles.items():
            if key in prompt:
                return enrich.NeedTitle(title=value)
        return enrich.NeedTitle(title="Tytuł bez dopasowania")

    monkeypatch.setattr(enrich, "embed_query", embed_text)
    monkeypatch.setattr(enrich, "embed_titles", embed_titles)
    monkeypatch.setattr(enrich, "run_agent", title)
    monkeypatch.setattr(clusters, "embed_titles", embed_titles)
    monkeypatch.setattr(service, "schedule_enrichment", lambda _: None)
    monkeypatch.setattr(service, "schedule_summary", lambda _: None)
    monkeypatch.setattr(enrich, "schedule_summary", lambda _: None)
    return titles
