import asyncio
import hashlib
import io
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from selectolax.parser import HTMLParser
from sqlmodel import col, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.ai import AiBudgetExceededError, AiUnavailableError
from services.bus import bus
from services.ingest import refresh_embeddings
from services.ingest.importer import CONTENT_FIELDS
from services.ingest.parse import (
    BASE_URL,
    ITEM_LINK,
    LIBRARY_PATH,
    ItemLink,
    parse_category,
    parse_item,
)
from services.library.images.stock import give_stock, target
from utils.db import session_scope
from utils.db.models import (
    Category,
    Innovation,
    InnovationStatus,
    KnowledgeStatus,
    Material,
    MaterialFile,
    MaterialKind,
    MaterialText,
    SummaryState,
)
from utils.logging import logger

from .documents import extract_text, is_pdf, normalize_page
from .materials import refresh_material_embeddings
from .safe_fetch import BlockedUrlError, fetch_limited, public_client
from .summaries import has_text, summarize

MAX_PDF_BYTES = 30 * 1024 * 1024
MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
TITLE_LIMIT = 200
MIN_TITLE = 5
JOBS_KEPT = 50
SECTION = "Dodane w HubMi"
STEPS = ("fetch", "text", "summary", "save", "embedding")
DROP_TAGS = "script, style, noscript, nav, header, footer, aside, form, svg, iframe"
ROPS_HOST = urlparse(BASE_URL).hostname

SourceKind = Literal["url", "pdf", "text"]


class AddError(Exception):
    def __init__(self, message: str, *, existing: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.existing = existing


@dataclass(frozen=True, slots=True)
class NewMaterial:
    kind: SourceKind
    url: str | None = None
    data: bytes | None = None
    filename: str | None = None
    text: str | None = None
    title: str | None = None
    material_kind: MaterialKind = MaterialKind.PUBLICATION
    year: int | None = None


@dataclass(slots=True)
class Prepared:
    title: str
    pages: list[str]
    fallback_title: str
    sha256: str
    size: int
    file_url: str | None
    stored: tuple[bytes, str, str] | None


jobs: OrderedDict[str, dict[str, Any]] = OrderedDict()
_tasks: set[asyncio.Task[None]] = set()


def _remember(job_id: str, payload: dict[str, Any]) -> None:
    jobs[job_id] = payload
    jobs.move_to_end(job_id)
    while len(jobs) > JOBS_KEPT:
        jobs.popitem(last=False)


def _progress(job_id: str, step: str) -> None:
    payload = {
        "job_id": job_id,
        "status": "running",
        "step": step,
        "done": STEPS.index(step),
        "total": len(STEPS),
    }
    _remember(job_id, payload)
    bus.publish("ingest.progress", payload)


def _finish(
    job_id: str,
    *,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    existing: dict[str, Any] | None = None,
) -> None:
    payload = {
        "job_id": job_id,
        "status": "failed" if error else "done",
        "result": result,
        "error": error,
        "existing": existing,
    }
    _remember(job_id, payload)
    bus.publish("ingest.finished", payload)


def clip_title(value: str) -> str:
    flat = " ".join(value.split())
    return flat[:TITLE_LIMIT].rstrip()


def html_text(html: bytes) -> tuple[str, list[str]]:
    tree = HTMLParser(html.decode("utf-8", errors="replace"))
    title = ""
    for selector in ('meta[property="og:title"]', "title", "h1"):
        node = tree.css_first(selector)
        value = (
            node.attributes.get("content") if node and node.tag == "meta" else None
        ) or (node.text() if node else "")
        if value and value.strip():
            title = value
            break
    for separator in (" | ", " - "):
        head = title.split(separator)[0]
        if separator in title and len(head.strip()) > MIN_TITLE:
            title = head
    for node in tree.css(DROP_TAGS):
        node.decompose()
    root = tree.css_first("main") or tree.css_first("article") or tree.body
    text = normalize_page(root.text(separator="\n")) if root else ""
    return clip_title(title), [text]


def first_line(pages: list[str]) -> str:
    for line in (pages[0] if pages else "").split("\n"):
        if len(line.strip()) > MIN_TITLE:
            return clip_title(line)
    return ""


def pdf_title(data: bytes) -> str:
    try:
        metadata = PdfReader(io.BytesIO(data)).metadata
    except (PdfReadError, ValueError, OSError):
        return ""
    value = clip_title(str(metadata.get("/Title") or "")) if metadata else ""
    if len(value) <= MIN_TITLE or value.lower().startswith(("microsoft", "untitled")):
        return ""
    return value


def is_rops_item(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.hostname == ROPS_HOST and ITEM_LINK.search(parsed.path) is not None


async def prepare(source: NewMaterial) -> Prepared:
    if source.kind == "text":
        text = normalize_page(source.text or "")
        data = text.encode()
        return Prepared(
            title=clip_title(source.title or ""),
            pages=[text],
            fallback_title=first_line([text]),
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
            file_url=None,
            stored=(data, "text/plain; charset=utf-8", "tekst.txt"),
        )
    if source.kind == "pdf":
        data = source.data or b""
        if not is_pdf(data):
            message = "To nie jest plik PDF."
            raise AddError(message)
        pages = (await extract_text(data)).pages
        return Prepared(
            title=clip_title(source.title or "") or pdf_title(data),
            pages=pages,
            fallback_title=first_line(pages),
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
            file_url=None,
            stored=(data, "application/pdf", source.filename or "material.pdf"),
        )
    url = source.url or ""
    async with public_client() as client:
        data, content_type = await fetch_limited(client, url, MAX_PDF_BYTES)
    if is_pdf(data):
        pages = (await extract_text(data)).pages
        title = clip_title(source.title or "") or pdf_title(data)
    elif (
        content_type in {"text/html", "application/xhtml+xml"}
        or data.lstrip()[:1] == b"<"
    ):
        if len(data) > MAX_PAGE_BYTES:
            message = "Strona jest za duża."
            raise AddError(message)
        found, pages = html_text(data)
        title = clip_title(source.title or "") or found
    else:
        message = "Pod tym adresem nie ma strony ani pliku PDF."
        raise AddError(message)
    return Prepared(
        title=title,
        pages=pages,
        fallback_title=first_line(pages),
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        file_url=url,
        stored=None,
    )


async def duplicate(session: AsyncSession, prepared: Prepared) -> Material | None:
    conditions = [col(Material.source_hash) == prepared.sha256]
    if prepared.file_url:
        conditions.append(col(Material.file_url) == prepared.file_url)
    return (await session.exec(select(Material).where(or_(*conditions)))).first()


async def add_material(job_id: str, source: NewMaterial) -> dict[str, Any]:
    _progress(job_id, "fetch")
    prepared = await prepare(source)
    _progress(job_id, "text")
    if not has_text(prepared.pages):
        message = "Nie udało się odczytać tekstu. Skan bez warstwy tekstowej?"
        raise AddError(message)
    async with session_scope() as session:
        found = await duplicate(session, prepared)
        if found is not None:
            message = "Ten materiał już jest w zasobach."
            raise AddError(
                message,
                existing={
                    "kind": "material",
                    "id": str(found.id),
                    "title": found.title,
                },
            )
    _progress(job_id, "summary")
    summary = await summarize(prepared.title or "(brak tytułu)", prepared.pages)
    if not summary.readable:
        message = "Tekst jest nieczytelny albo to nie jest publikacja."
        raise AddError(message)
    title = prepared.title or summary.title or prepared.fallback_title
    if not title:
        message = "Podaj tytuł materiału."
        raise AddError(message)
    _progress(job_id, "save")
    material_id = uuid.uuid4()
    own_url = f"/api/materials/{material_id}/file"
    file_url = prepared.file_url or own_url
    async with session_scope() as session:
        material = Material(
            id=material_id,
            kind=source.material_kind,
            title=title,
            year=source.year,
            summary=summary.summary,
            topics=summary.topics,
            file_url=file_url,
            source_url=file_url,
            source_section=SECTION,
            file_size=prepared.size,
            pages=len(prepared.pages) or None,
            source_hash=prepared.sha256,
            summary_state=SummaryState.DONE,
            summary_hash=prepared.sha256,
            status=KnowledgeStatus.DRAFT,
            imported_at=datetime.now(UTC),
        )
        session.add(material)
        await session.flush()
        session.add(
            MaterialText(
                material_id=material_id,
                pages=prepared.pages,
                chars=sum(len(p) for p in prepared.pages),
            )
        )
        if prepared.stored is not None:
            data, mime_type, filename = prepared.stored
            session.add(
                MaterialFile(
                    material_id=material_id,
                    data=data,
                    mime_type=mime_type,
                    filename=filename,
                )
            )
        await session.commit()
        _progress(job_id, "embedding")
        await refresh_material_embeddings(session)
    return {"kind": "material", "id": str(material_id), "title": title}


async def add_innovation(job_id: str, url: str) -> dict[str, Any]:
    _progress(job_id, "fetch")
    match = ITEM_LINK.search(urlparse(url).path)
    if match is None:
        message = "To nie jest adres innowacji z biblioteki ROPS."
        raise AddError(message)
    slug, category_slug = match["slug"], match["category"]
    page_url = f"{BASE_URL}{LIBRARY_PATH}/{category_slug},{slug}"
    async with public_client() as client:
        html, _ = await fetch_limited(client, page_url, MAX_PAGE_BYTES)
        category_html, _ = await fetch_limited(
            client, f"{BASE_URL}{LIBRARY_PATH}/{category_slug}", MAX_PAGE_BYTES
        )
    lead = next(
        (
            i.lead
            for i in parse_category(category_html.decode()).items
            if i.slug == slug
        ),
        "",
    )
    _progress(job_id, "text")
    item = parse_item(
        html.decode(),
        ItemLink(slug=slug, category_slug=category_slug, url=page_url, lead=lead),
    )
    async with session_scope() as session:
        current = (
            await session.exec(
                select(Innovation).where(
                    or_(
                        col(Innovation.source_url) == item.source_url,
                        col(Innovation.slug) == item.slug,
                    )
                )
            )
        ).first()
        if current is not None:
            message = "Ta innowacja już jest w bibliotece."
            raise AddError(
                message,
                existing={
                    "kind": "innovation",
                    "slug": current.slug,
                    "title": current.title,
                },
            )
        category = (
            await session.exec(
                select(Category).where(col(Category.slug) == item.category_slug)
            )
        ).first()
        if category is None:
            message = "Nieznana kategoria tej innowacji."
            raise AddError(message)
        _progress(job_id, "save")
        innovation = Innovation(
            slug=item.slug,
            source_url=item.source_url,
            source_hash=item.content_hash(),
            imported_at=datetime.now(UTC),
            status=InnovationStatus.DRAFT,
            **{name: getattr(item, name) for name in CONTENT_FIELDS},
        )
        session.add(innovation)
        await session.commit()
        _progress(job_id, "embedding")
        await refresh_embeddings(session)
        await give_stock(session, target(innovation))
    return {"kind": "innovation", "slug": item.slug, "title": item.title}


async def run_job(job_id: str, source: NewMaterial) -> None:
    try:
        if source.kind == "url" and source.url and is_rops_item(source.url):
            result = await add_innovation(job_id, source.url)
        else:
            result = await add_material(job_id, source)
    except AddError as e:
        _finish(job_id, error=e.message, existing=e.existing)
    except BlockedUrlError:
        _finish(job_id, error="Tego adresu nie możemy otworzyć.")
    except (AiUnavailableError, AiBudgetExceededError):
        _finish(job_id, error="Opis AI jest teraz niedostępny. Spróbuj za chwilę.")
    except Exception:
        logger.exception("adding material %s failed", job_id)
        _finish(job_id, error="Nie udało się dodać materiału.")
    else:
        _finish(job_id, result=result)


def start(source: NewMaterial) -> str:
    job_id = str(uuid.uuid4())
    _remember(
        job_id,
        {
            "job_id": job_id,
            "status": "running",
            "step": "fetch",
            "done": 0,
            "total": len(STEPS),
        },
    )
    task = asyncio.create_task(run_job(job_id, source))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return job_id


def job(job_id: str) -> dict[str, Any] | None:
    return jobs.get(job_id)


def valid_text(value: str) -> bool:
    return bool(value.strip()) and len(value) <= MAX_TEXT_CHARS and "\x00" not in value
