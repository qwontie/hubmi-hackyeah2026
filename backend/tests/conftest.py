import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlmodel import col, delete, select

from utils.db import session_scope
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
