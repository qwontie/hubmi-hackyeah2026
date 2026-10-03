from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession


async def init_db() -> None:
    from . import models  # noqa: F401, PLC0415


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession]:
    from dependencies.container import container  # noqa: PLC0415

    maker = await container.get(async_sessionmaker[AsyncSession])
    async with maker() as session:
        yield session
