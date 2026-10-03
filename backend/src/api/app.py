from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from api import errors, routers
from api.middleware import SameOriginMiddleware
from dependencies.container import container
from services.mail import StaffNotifier
from services.schedule import start_schedule, stop_schedule
from utils.db import init_db
from utils.env import env, validate_prod_settings
from utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncGenerator[None]:
    setup_logging()
    validate_prod_settings()
    await init_db()
    await app_.state.dishka_container.get(StaffNotifier)
    schedule = start_schedule()
    yield
    await stop_schedule(schedule)
    await app_.state.dishka_container.close()


app = FastAPI(
    title="hubmi API",
    lifespan=lifespan,
    openapi_url="/openapi.json" if env.api.docs else None,
)

app.add_middleware(SameOriginMiddleware)

errors.install(app)

app.include_router(routers.router)

setup_dishka(container, app)
