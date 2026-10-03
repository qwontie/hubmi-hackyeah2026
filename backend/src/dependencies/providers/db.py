from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.env import env


class DbProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_engine(self) -> AsyncGenerator[AsyncEngine]:
        engine = create_async_engine(
            env.db.async_connection_url,
            pool_size=env.db.min_pool_size,
            max_overflow=env.db.max_pool_size - env.db.min_pool_size,
            pool_pre_ping=True,
        )
        try:
            yield engine
        finally:
            await engine.dispose()

    @provide(scope=Scope.APP)
    def get_sessionmaker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, maker: async_sessionmaker[AsyncSession]
    ) -> AsyncGenerator[AsyncSession]:
        async with maker() as session:
            yield session
