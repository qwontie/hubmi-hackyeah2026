import asyncio
import contextlib
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import func, select
from sqlmodel import col

from services.ai.costs import use_budget_scope
from services.ingest import ImportAlreadyRunningError, run_import
from services.knowledge import KnowledgeImportRunningError, run_knowledge_import
from utils.db import session_scope
from utils.db.models import ImportRun, ImportTrigger, KnowledgeRun
from utils.logging import logger


class ScheduleSettings(BaseSettings):
    enabled: bool = True
    at: time = time(3, 30)
    timezone: str = "Europe/Warsaw"
    check_seconds: int = 300

    model_config = SettingsConfigDict(
        env_prefix="SCHEDULE__", env_file=("../.env", ".env"), extra="ignore"
    )


def last_slot(now: datetime, settings: ScheduleSettings) -> datetime:
    zone = ZoneInfo(settings.timezone)
    local = now.astimezone(zone)
    slot = datetime.combine(local.date(), settings.at, tzinfo=zone)
    if slot > local:
        slot -= timedelta(days=1)
    return slot.astimezone(UTC)


async def last_run(model: type[ImportRun] | type[KnowledgeRun]) -> datetime | None:
    async with session_scope() as session:
        return await session.scalar(
            select(func.max(model.started_at)).where(
                col(model.trigger) == ImportTrigger.SCHEDULE
            )
        )


async def run_library() -> None:
    try:
        run = await run_import(trigger=ImportTrigger.SCHEDULE)
    except ImportAlreadyRunningError:
        logger.info("schedule: library import already running, retry later")
        return
    logger.info(
        "schedule: library import %s created=%d updated=%d unchanged=%d failed=%d",
        run.status.value,
        run.created,
        run.updated,
        run.unchanged,
        run.failed,
    )


async def run_knowledge() -> None:
    try:
        run = await run_knowledge_import(trigger=ImportTrigger.SCHEDULE)
    except KnowledgeImportRunningError:
        logger.info("schedule: knowledge import already running, retry later")
        return
    logger.info("schedule: knowledge import %s %s", run.status.value, run.counters)


async def tick(settings: ScheduleSettings) -> None:
    slot = last_slot(datetime.now(UTC), settings)
    jobs = ((ImportRun, run_library), (KnowledgeRun, run_knowledge))
    for model, job in jobs:
        last = await last_run(model)
        if last is None or last < slot:
            logger.info("schedule: %s due (slot %s)", model.__tablename__, slot)
            with use_budget_scope("batch"):
                await job()


async def loop(settings: ScheduleSettings) -> None:
    logger.info(
        "schedule: daily import at %s %s",
        settings.at.strftime("%H:%M"),
        settings.timezone,
    )
    while True:
        try:
            await tick(settings)
        except Exception:
            logger.exception("schedule: daily import failed")
        await asyncio.sleep(settings.check_seconds)


def start_schedule(
    settings: ScheduleSettings | None = None,
) -> asyncio.Task[None] | None:
    settings = settings or ScheduleSettings()
    if not settings.enabled:
        logger.info("schedule: daily import is off")
        return None
    return asyncio.create_task(loop(settings))


async def stop_schedule(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
