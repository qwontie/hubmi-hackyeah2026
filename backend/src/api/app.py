from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import routers
from dependencies.container import container
from utils.db import init_db
from utils.env import env
from utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncGenerator[None]:
    setup_logging()
    await init_db()
    yield
    await app_.state.dishka_container.close()


app = FastAPI(
    title="hubmi API",
    lifespan=lifespan,
    openapi_url="/openapi.json" if env.api.docs else None,
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(routers.router)

setup_dishka(container, app)
