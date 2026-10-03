import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import ColumnElement, Float, func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.ai import AiBudgetExceededError, AiUnavailableError, embed_documents
from services.ingest.fetch import PageFetcher
from services.search.text import keyword_terms
from services.search.vector import cosine_distance
from utils.db.models.material import (
    KnowledgeStatus,
    Material,
    MaterialKind,
    SummaryState,
)
from utils.db.models.material_text import MaterialText
from utils.logging import logger

from .documents import download, extract_text, remote_size
from .sources import MaterialLink
from .summaries import has_text, summarize
from .topics import TOPICS

LINK_FIELDS = ("kind", "title", "year", "source_url", "source_section")
MAX_EMBED_CHARS = 4000


@dataclass(slots=True)
class MaterialCounters:
    total: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    summarized: int = 0
    no_text: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


async def find_by_url(session: AsyncSession, file_url: str) -> Material | None:
    return (
        await session.exec(select(Material).where(Material.file_url == file_url))
    ).first()


async def stored_text(session: AsyncSession, material_id: uuid.UUID) -> list[str]:
    row = await session.get(MaterialText, material_id)
    return list(row.pages) if row else []


async def _store_text(
    session: AsyncSession, material_id: uuid.UUID, pages: list[str]
) -> None:
    row = await session.get(MaterialText, material_id)
    if row is None:
        row = MaterialText(material_id=material_id)
    row.pages = pages
    row.chars = sum(len(page) for page in pages)
    session.add(row)


def _apply_link(material: Material, link: MaterialLink) -> bool:
    protected = set(material.edited_fields)
    changed = False
    values = {
        "kind": link.kind,
        "title": link.title,
        "year": link.year,
        "source_url": link.source_url,
        "source_section": link.section,
    }
    for name, value in values.items():
        if name in protected or getattr(material, name) == value:
            continue
        setattr(material, name, value)
        changed = True
    return changed


async def _summarize_into(
    material: Material, pages: list[str], counters: MaterialCounters
) -> None:
    if material.summary_hash == material.source_hash and material.summary_state in {
        SummaryState.DONE,
        SummaryState.NO_TEXT,
    }:
        return
    protected = set(material.edited_fields)
    if not has_text(pages):
        material.summary_state = SummaryState.NO_TEXT
        material.summary_hash = material.source_hash
        counters.no_text += 1
        return
    try:
        result = await summarize(material.title, pages)
    except AiBudgetExceededError:
        raise
    except AiUnavailableError as e:
        material.summary_state = SummaryState.FAILED
        counters.errors.append(f"{material.file_url}: {e!r}"[:300])
        return
    if "summary" not in protected:
        material.summary = result.summary
    if "topics" not in protected:
        material.topics = result.topics
    material.summary_state = (
        SummaryState.DONE if result.readable else SummaryState.NO_TEXT
    )
    material.summary_hash = material.source_hash
    counters.summarized += 1


async def import_material(  # noqa: PLR0913
    session: AsyncSession,
    fetcher: PageFetcher,
    link: MaterialLink,
    counters: MaterialCounters,
    *,
    cache_dir: Path | None = None,
    force: bool = False,
) -> Material:
    now = datetime.now(UTC)
    material = await find_by_url(session, link.file_url)
    created = material is None
    if material is None:
        material = Material(
            kind=link.kind,
            title=link.title,
            year=link.year,
            file_url=link.file_url,
            source_url=link.source_url,
            source_section=link.section,
            status=KnowledgeStatus.PUBLISHED,
        )
        session.add(material)
        await session.flush()
    link_changed = _apply_link(material, link)
    pages: list[str] | None = None
    file_changed = False
    known = material.source_hash is not None and material.file_size is not None
    size = None if (force or not known) else await remote_size(fetcher, link.file_url)
    if not known or force or size != material.file_size:
        document = await download(fetcher, link.file_url, cache_dir=cache_dir)
        if document.sha256 != material.source_hash or force:
            extracted = await extract_text(document.data)
            pages = extracted.pages
            await _store_text(session, material.id, pages)
            material.pages = len(pages) or None
            file_changed = document.sha256 != material.source_hash
            material.source_hash = document.sha256
        material.file_size = len(document.data)
    if pages is None:
        pages = await stored_text(session, material.id)
    before = (material.summary_hash, material.summary_state)
    await _summarize_into(material, pages, counters)
    summary_changed = before != (material.summary_hash, material.summary_state)
    material.imported_at = now
    session.add(material)
    await session.commit()
    if created:
        counters.created += 1
    elif link_changed or file_changed or summary_changed:
        counters.updated += 1
    else:
        counters.unchanged += 1
    return material


def embedding_text(material: Material) -> str:
    topics = ", ".join(TOPICS.get(t, t) for t in material.topics)
    parts = [material.title, material.summary, f"Tematy: {topics}" if topics else ""]
    return "\n\n".join(p for p in parts if p.strip())[:MAX_EMBED_CHARS]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def refresh_material_embeddings(session: AsyncSession) -> int:
    rows = (await session.exec(select(Material))).all()
    todo: list[tuple[Material, str]] = []
    for row in rows:
        text = embedding_text(row)
        if row.embedding is None or row.embedded_hash != text_hash(text):
            todo.append((row, text))
    if not todo:
        return 0
    vectors = await embed_documents([t for _, t in todo], kind="embed_material")
    for (row, text), vector in zip(todo, vectors, strict=True):
        row.embedding = vector
        row.embedded_hash = text_hash(text)
        session.add(row)
    await session.commit()
    return len(todo)


async def related_materials(
    session: AsyncSession,
    vector: Sequence[float],
    *,
    limit: int = 3,
    exclude_ids: Sequence[uuid.UUID] = (),
    min_score: float = 0.0,
) -> list[tuple[Material, float]]:
    distance = cosine_distance(Material.embedding, list(vector))
    score = (1 - distance).cast(Float).label("score")
    statement = (
        select(Material, score)
        .where(
            Material.status == KnowledgeStatus.PUBLISHED,
            col(Material.embedding).is_not(None),
        )
        .order_by(distance)
        .limit(limit)
    )
    if exclude_ids:
        statement = statement.where(col(Material.id).not_in(list(exclude_ids)))
    rows = (await session.exec(statement)).all()
    return [(row[0], float(row[1])) for row in rows if float(row[1]) >= min_score]


@dataclass(frozen=True, slots=True)
class MaterialFilters:
    kind: MaterialKind | None = None
    topic: str | None = None
    year: int | None = None
    q: str | None = None
    status: KnowledgeStatus | None = KnowledgeStatus.PUBLISHED
    edited: bool | None = None


def _conditions(filters: MaterialFilters) -> list:
    conditions: list = []
    if filters.status is not None:
        conditions.append(Material.status == filters.status)
    if filters.kind is not None:
        conditions.append(Material.kind == filters.kind)
    if filters.topic:
        conditions.append(col(Material.topics).contains([filters.topic]))
    if filters.year is not None:
        conditions.append(Material.year == filters.year)
    if filters.edited is True:
        conditions.append(func.cardinality(col(Material.edited_fields)) > 0)
    if filters.edited is False:
        conditions.append(func.cardinality(col(Material.edited_fields)) == 0)
    return conditions


def ts_query(q: str) -> ColumnElement[Any] | None:
    terms = keyword_terms(q)
    if not terms:
        return None
    return func.to_tsquery("simple", " & ".join(terms))


async def list_materials(
    session: AsyncSession, filters: MaterialFilters, *, page: int, per_page: int
) -> tuple[list[Material], int]:
    conditions = _conditions(filters)
    statement = select(Material).where(*conditions)
    count_statement = select(func.count()).select_from(Material).where(*conditions)
    query = ts_query(filters.q) if filters.q else None
    if query is not None:
        matches = col(Material.search).op("@@")(query)
        statement = statement.where(matches).order_by(
            func.ts_rank_cd(col(Material.search), query).desc(),
            col(Material.year).desc().nulls_last(),
        )
        count_statement = count_statement.where(matches)
    else:
        statement = statement.order_by(
            col(Material.year).desc().nulls_last(), col(Material.title)
        )
    total = int((await session.exec(count_statement)).one())
    rows = (
        await session.exec(statement.offset((page - 1) * per_page).limit(per_page))
    ).all()
    return list(rows), total


async def topic_counts(session: AsyncSession) -> dict[str, int]:
    topic = func.unnest(col(Material.topics)).label("topic")
    subquery = (
        select(topic).where(Material.status == KnowledgeStatus.PUBLISHED).subquery()
    )
    rows = (
        await session.exec(
            select(subquery.c.topic, func.count()).group_by(subquery.c.topic)
        )
    ).all()
    return {str(row[0]): int(row[1]) for row in rows}


async def get_material(
    session: AsyncSession, material_id: uuid.UUID, *, published_only: bool = True
) -> Material | None:
    material = await session.get(Material, material_id)
    if material is None:
        return None
    if published_only and material.status != KnowledgeStatus.PUBLISHED:
        return None
    return material


def log_counters(counters: MaterialCounters) -> None:
    logger.info(
        "materials: total=%d created=%d updated=%d unchanged=%d summarized=%d "
        "no_text=%d failed=%d",
        counters.total,
        counters.created,
        counters.updated,
        counters.unchanged,
        counters.summarized,
        counters.no_text,
        counters.failed,
    )
