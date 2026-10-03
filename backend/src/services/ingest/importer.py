import asyncio
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlmodel import col, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.bus import bus
from utils.db import session_scope
from utils.db.models.category import Category
from utils.db.models.import_run import ImportRun, ImportStatus, ImportTrigger
from utils.db.models.innovation import Innovation, InnovationStatus
from utils.logging import logger

from .embeddings import refresh_embeddings
from .fetch import PageFetcher
from .parse import (
    CATEGORIES_URL,
    CategoryLink,
    ItemLink,
    ScrapedInnovation,
    parse_categories,
    parse_category,
    parse_item,
)

IMPORT_LOCK_KEY = 0x48554D49
CONTENT_FIELDS = (
    "category_slug",
    "title",
    "lead",
    "what_it_is",
    "problems",
    "target_group",
    "who_can_use",
    "effectiveness",
    "authors",
    "qr_url",
    "video_url",
    "materials_url",
    "brochure_url",
    "license",
)

Progress = Callable[[dict[str, Any]], None]


class ImportAlreadyRunningError(RuntimeError):
    pass


@dataclass(slots=True)
class Counters:
    total: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped_edited: int = 0
    failed: int = 0


def run_payload(run: ImportRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "status": run.status.value,
        "trigger": run.trigger.value,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "total": run.total,
        "created": run.created,
        "updated": run.updated,
        "unchanged": run.unchanged,
        "skipped_edited": run.skipped_edited,
        "failed": run.failed,
        "error": run.error,
    }


async def _upsert_categories(
    session: AsyncSession, links: list[CategoryLink], names: dict[str, str]
) -> None:
    existing = {c.slug: c for c in (await session.exec(select(Category))).all()}
    for link in links:
        category = existing.get(link.slug) or Category(
            slug=link.slug, name=link.name, source_url=link.url
        )
        category.name = names.get(link.slug) or link.name or link.slug
        category.source_url = link.url
        category.position = link.position
        session.add(category)
    await session.commit()


async def _set_category_icon(
    session: AsyncSession, slug: str, icon_url: str | None
) -> None:
    if not icon_url:
        return
    category = (
        await session.exec(select(Category).where(Category.slug == slug))
    ).first()
    if category is not None and category.icon_url != icon_url:
        category.icon_url = icon_url
        session.add(category)


async def _find(session: AsyncSession, item: ScrapedInnovation) -> Innovation | None:
    return (
        await session.exec(
            select(Innovation).where(
                or_(
                    col(Innovation.source_url) == item.source_url,
                    col(Innovation.slug) == item.slug,
                )
            )
        )
    ).first()


async def _upsert_item(
    session: AsyncSession, item: ScrapedInnovation, counters: Counters
) -> None:
    now = datetime.now(UTC)
    digest = item.content_hash()
    current = await _find(session, item)
    if current is None:
        session.add(
            Innovation(
                slug=item.slug,
                source_url=item.source_url,
                source_hash=digest,
                imported_at=now,
                status=InnovationStatus.PUBLISHED,
                **{name: getattr(item, name) for name in CONTENT_FIELDS},
            )
        )
        counters.created += 1
        return
    if current.source_hash == digest and current.source_url == item.source_url:
        counters.unchanged += 1
        return
    protected = set(current.edited_fields)
    changed = False
    skipped = False
    for name in CONTENT_FIELDS:
        value = getattr(item, name)
        if getattr(current, name) == value:
            continue
        if name in protected:
            skipped = True
            continue
        setattr(current, name, value)
        changed = True
    current.source_url = item.source_url
    current.source_hash = digest
    current.imported_at = now
    session.add(current)
    if changed:
        counters.updated += 1
    elif skipped:
        counters.skipped_edited += 1
    else:
        counters.unchanged += 1
    if changed and skipped:
        counters.skipped_edited += 1


async def _close_stale_runs(session: AsyncSession, keep: uuid.UUID | None) -> None:
    stale = (
        await session.exec(
            select(ImportRun).where(
                ImportRun.status == ImportStatus.RUNNING, col(ImportRun.id) != keep
            )
        )
    ).all()
    for run in stale:
        run.status = ImportStatus.FAILED
        run.error = "interrupted"
        run.finished_at = datetime.now(UTC)
        session.add(run)
    await session.commit()


def _emit(progress: Progress | None, payload: dict[str, Any]) -> None:
    bus.publish("import.progress", payload)
    if progress is not None:
        progress(payload)


async def _finish(
    session: AsyncSession,
    run: ImportRun,
    counters: Counters,
    *,
    error: str | None = None,
) -> ImportRun:
    for name, value in asdict(counters).items():
        setattr(run, name, value)
    run.status = ImportStatus.FAILED if error else ImportStatus.DONE
    run.error = error
    run.finished_at = datetime.now(UTC)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    bus.publish("import.finished", run_payload(run))
    return run


async def _crawl(
    session: AsyncSession,
    fetcher: PageFetcher,
    run: ImportRun,
    counters: Counters,
    progress: Progress | None,
) -> None:
    category_links = parse_categories(await fetcher.get(CATEGORIES_URL))
    if not category_links:
        msg = "no categories found on the ROPS library page"
        raise RuntimeError(msg)
    names: dict[str, str] = {}
    items: list[ItemLink] = []
    for link in category_links:
        page = parse_category(await fetcher.get(link.url))
        names[link.slug] = page.name
        items.extend(page.items)
    await _upsert_categories(session, category_links, names)
    counters.total = len(items)
    run.total = counters.total
    session.add(run)
    await session.commit()

    for done, link in enumerate(items, start=1):
        try:
            item = parse_item(await fetcher.get(link.url), link)
            await _set_category_icon(
                session, item.category_slug, item.category_icon_url
            )
            await _upsert_item(session, item, counters)
            await session.commit()
        except Exception:
            await session.rollback()
            counters.failed += 1
            logger.exception("import: item %s failed", link.url)
        _emit(
            progress,
            {"run_id": str(run.id), "done": done, "current": link.slug}
            | asdict(counters),
        )


async def run_import(
    *,
    trigger: ImportTrigger,
    run_id: uuid.UUID | None = None,
    cache_dir: Path | None = None,
    delay: float = 1.0,
    progress: Progress | None = None,
) -> ImportRun:
    async with session_scope() as lock_session:
        locked = await lock_session.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": IMPORT_LOCK_KEY}
        )
        if not locked:
            raise ImportAlreadyRunningError
        try:
            async with session_scope() as session:
                await _close_stale_runs(session, run_id)
                run = (await session.get(ImportRun, run_id)) if run_id else None
                if run is None:
                    run = ImportRun(trigger=trigger, status=ImportStatus.RUNNING)
                    session.add(run)
                    await session.commit()
                    await session.refresh(run)
                counters = Counters()
                try:
                    async with PageFetcher(delay=delay, cache_dir=cache_dir) as fetcher:
                        await _crawl(session, fetcher, run, counters, progress)
                    embedded = await refresh_embeddings(session)
                    logger.info("import: embedded %d innovations", embedded)
                except Exception as e:
                    await session.rollback()
                    logger.exception("import failed")
                    return await _finish(session, run, counters, error=repr(e)[:500])
                return await _finish(session, run, counters)
        finally:
            await lock_session.scalar(
                text("SELECT pg_advisory_unlock(:key)"), {"key": IMPORT_LOCK_KEY}
            )


async def latest_runs(session: AsyncSession, limit: int = 20) -> list[ImportRun]:
    return list(
        (
            await session.exec(
                select(ImportRun)
                .order_by(col(ImportRun.started_at).desc())
                .limit(limit)
            )
        ).all()
    )


_background: set[asyncio.Task[ImportRun]] = set()


async def start_import(*, trigger: ImportTrigger = ImportTrigger.ADMIN) -> ImportRun:
    if any(not task.done() for task in _background):
        raise ImportAlreadyRunningError
    async with session_scope() as session:
        locked = await session.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": IMPORT_LOCK_KEY}
        )
        if not locked:
            raise ImportAlreadyRunningError
        await session.scalar(
            text("SELECT pg_advisory_unlock(:key)"), {"key": IMPORT_LOCK_KEY}
        )
        run = ImportRun(trigger=trigger, status=ImportStatus.RUNNING)
        session.add(run)
        await session.commit()
        await session.refresh(run)
    task = asyncio.create_task(run_import(trigger=trigger, run_id=run.id))
    _background.add(task)
    task.add_done_callback(_background.discard)
    return run
