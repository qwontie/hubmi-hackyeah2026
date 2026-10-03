import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.ai import AiBudgetExceededError
from services.bus import bus
from services.ingest.fetch import PageFetcher
from utils.db import session_scope
from utils.db.models.import_run import ImportStatus, ImportTrigger
from utils.db.models.knowledge_run import KnowledgeRun
from utils.logging import logger

from .materials import (
    MaterialCounters,
    import_material,
    log_counters,
    refresh_material_embeddings,
)
from .sources import LISTINGS, MaterialLink, dedupe, map_of_challenges

KNOWLEDGE_LOCK_KEY = 0x4B4E4F57
STEPS = ("materials", "challenges", "figures")

Progress = Callable[[dict[str, Any]], None]
Step = Callable[["RunContext"], Awaitable[dict[str, Any]]]


class KnowledgeImportRunningError(RuntimeError):
    pass


class RunContext:
    def __init__(  # noqa: PLR0913
        self,
        session: AsyncSession,
        run: KnowledgeRun,
        fetcher: PageFetcher,
        *,
        cache_dir: Path | None,
        force: bool,
        progress: Progress | None,
    ) -> None:
        self.session = session
        self.run = run
        self.fetcher = fetcher
        self.cache_dir = cache_dir
        self.force = force
        self.progress = progress
        self.counters: dict[str, Any] = {}

    async def emit(
        self, step: str, done: int, total: int, current: str, counters: dict[str, Any]
    ) -> None:
        self.counters[step] = counters
        self.run.step = step
        self.run.done = done
        self.run.total = total
        self.run.counters = dict(self.counters)
        self.session.add(self.run)
        await self.session.commit()
        payload = {
            "run_id": str(self.run.id),
            "step": step,
            "done": done,
            "total": total,
            "current": current,
            "counters": counters,
        }
        bus.publish("knowledge.import.progress", payload)
        if self.progress is not None:
            self.progress(payload)


def run_payload(run: KnowledgeRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "status": run.status.value,
        "trigger": run.trigger.value,
        "step": run.step,
        "done": run.done,
        "total": run.total,
        "counters": run.counters,
        "error": run.error,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


async def collect_links(fetcher: PageFetcher) -> list[MaterialLink]:
    links: list[MaterialLink] = [map_of_challenges()]
    for url, parse in LISTINGS:
        found = parse(await fetcher.get(url))
        if not found:
            logger.warning("knowledge: no materials found on %s", url)
        links.extend(found)
    return dedupe(links)


async def step_materials(ctx: RunContext) -> dict[str, Any]:
    links = await collect_links(ctx.fetcher)
    counters = MaterialCounters(total=len(links))
    for done, link in enumerate(links, start=1):
        try:
            await import_material(
                ctx.session,
                ctx.fetcher,
                link,
                counters,
                cache_dir=ctx.cache_dir,
                force=ctx.force,
            )
        except AiBudgetExceededError:
            raise
        except Exception as e:
            await ctx.session.rollback()
            counters.failed += 1
            counters.errors.append(f"{link.file_url}: {e!r}"[:300])
            logger.exception("knowledge: material %s failed", link.file_url)
        await ctx.emit(
            "materials", done, len(links), link.title, _public(asdict(counters))
        )
    embedded = await refresh_material_embeddings(ctx.session)
    log_counters(counters)
    result = _public(asdict(counters)) | {"embedded": embedded}
    await ctx.emit("materials", len(links), len(links), "", result)
    return result


def _public(counters: dict[str, Any]) -> dict[str, Any]:
    errors = counters.pop("errors", [])
    return counters | {"errors": errors[-5:]}


async def _close_stale(session: AsyncSession, keep: uuid.UUID | None) -> None:
    stale = (
        await session.exec(
            select(KnowledgeRun).where(
                KnowledgeRun.status == ImportStatus.RUNNING,
                col(KnowledgeRun.id) != keep,
            )
        )
    ).all()
    for run in stale:
        run.status = ImportStatus.FAILED
        run.error = "interrupted"
        run.finished_at = datetime.now(UTC)
        session.add(run)
    await session.commit()


async def _finish(
    session: AsyncSession, run: KnowledgeRun, *, error: str | None = None
) -> KnowledgeRun:
    run.status = ImportStatus.FAILED if error else ImportStatus.DONE
    run.error = error
    run.finished_at = datetime.now(UTC)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    bus.publish("knowledge.import.finished", run_payload(run))
    return run


def _steps() -> dict[str, Step]:
    from .challenges import step_challenges, step_figures  # noqa: PLC0415

    return {
        "materials": step_materials,
        "challenges": step_challenges,
        "figures": step_figures,
    }


async def run_knowledge_import(  # noqa: PLR0913
    *,
    trigger: ImportTrigger,
    run_id: uuid.UUID | None = None,
    steps: tuple[str, ...] = STEPS,
    cache_dir: Path | None = None,
    delay: float = 1.0,
    force: bool = False,
    progress: Progress | None = None,
) -> KnowledgeRun:
    async with session_scope() as lock_session:
        locked = await lock_session.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": KNOWLEDGE_LOCK_KEY}
        )
        if not locked:
            raise KnowledgeImportRunningError
        try:
            async with session_scope() as session:
                await _close_stale(session, run_id)
                run = (await session.get(KnowledgeRun, run_id)) if run_id else None
                if run is None:
                    run = KnowledgeRun(trigger=trigger, status=ImportStatus.RUNNING)
                    session.add(run)
                    await session.commit()
                    await session.refresh(run)
                available = _steps()
                try:
                    async with PageFetcher(delay=delay) as fetcher:
                        ctx = RunContext(
                            session,
                            run,
                            fetcher,
                            cache_dir=cache_dir,
                            force=force,
                            progress=progress,
                        )
                        for name in steps:
                            await available[name](ctx)
                except Exception as e:
                    await session.rollback()
                    logger.exception("knowledge import failed")
                    return await _finish(session, run, error=repr(e)[:500])
                return await _finish(session, run)
        finally:
            await lock_session.scalar(
                text("SELECT pg_advisory_unlock(:key)"), {"key": KNOWLEDGE_LOCK_KEY}
            )


_background: set[asyncio.Task[KnowledgeRun]] = set()


async def start_knowledge_import(
    *, trigger: ImportTrigger = ImportTrigger.ADMIN
) -> KnowledgeRun:
    if any(not task.done() for task in _background):
        raise KnowledgeImportRunningError
    async with session_scope() as session:
        locked = await session.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": KNOWLEDGE_LOCK_KEY}
        )
        if not locked:
            raise KnowledgeImportRunningError
        await session.scalar(
            text("SELECT pg_advisory_unlock(:key)"), {"key": KNOWLEDGE_LOCK_KEY}
        )
        run = KnowledgeRun(trigger=trigger, status=ImportStatus.RUNNING)
        session.add(run)
        await session.commit()
        await session.refresh(run)
    task = asyncio.create_task(run_knowledge_import(trigger=trigger, run_id=run.id))
    _background.add(task)
    task.add_done_callback(_background.discard)
    return run


async def latest_runs(session: AsyncSession, limit: int = 20) -> list[KnowledgeRun]:
    return list(
        (
            await session.exec(
                select(KnowledgeRun)
                .order_by(col(KnowledgeRun.started_at).desc())
                .limit(limit)
            )
        ).all()
    )
