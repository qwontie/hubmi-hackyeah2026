import asyncio
import hashlib
import io
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from pypdf import PdfReader

from services.ingest.fetch import RETRIES, PageFetcher
from utils.logging import logger

MAX_BYTES = 60 * 1024 * 1024
logging.getLogger("pypdf").setLevel(logging.ERROR)
HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
SPACES = re.compile(r"[ \t ]+")
BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True, slots=True)
class Document:
    data: bytes
    sha256: str
    etag: str | None = None
    modified: str | None = None


@dataclass(frozen=True, slots=True)
class Validators:
    etag: str | None
    modified: str | None

    def headers(self) -> dict[str, str]:
        found: dict[str, str] = {}
        if self.etag:
            found["If-None-Match"] = self.etag
        if self.modified:
            found["If-Modified-Since"] = self.modified
        return found


@dataclass(frozen=True, slots=True)
class ExtractedText:
    pages: list[str]

    @property
    def chars(self) -> int:
        return sum(len(page) for page in self.pages)


def _cache_path(cache_dir: Path | None, url: str) -> Path | None:
    if cache_dir is None:
        return None
    return cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()[:32]}.bin"


async def download(
    fetcher: PageFetcher,
    url: str,
    *,
    cache_dir: Path | None = None,
    validators: Validators | None = None,
) -> Document | None:
    cached = _cache_path(cache_dir, url)
    if cached is not None and cached.exists():
        data = cached.read_bytes()
        return Document(data=data, sha256=hashlib.sha256(data).hexdigest())
    headers = validators.headers() if validators else {}
    last_error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            response = await fetcher.client.get(url, headers=headers)
            if response.status_code == httpx.codes.NOT_MODIFIED and headers:
                await asyncio.sleep(fetcher.delay)
                return None
            response.raise_for_status()
        except httpx.HTTPError as e:
            last_error = e
            logger.warning("download %s failed (%d): %r", url, attempt + 1, e)
            await asyncio.sleep(fetcher.delay * (attempt + 2))
            continue
        await asyncio.sleep(fetcher.delay)
        data = response.content
        if len(data) > MAX_BYTES:
            msg = f"{url} is larger than {MAX_BYTES} bytes"
            raise RuntimeError(msg)
        if cached is not None:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(data)
        return Document(
            data=data,
            sha256=hashlib.sha256(data).hexdigest(),
            etag=response.headers.get("etag"),
            modified=response.headers.get("last-modified"),
        )
    msg = f"cannot download {url}"
    raise RuntimeError(msg) from last_error


def normalize_page(text: str) -> str:
    text = HYPHEN_BREAK.sub(r"\1\2", text.replace("\r", "").replace("\x00", ""))
    text = SPACES.sub(" ", text)
    lines = [line.strip() for line in text.split("\n")]
    return BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def _extract(data: bytes) -> ExtractedText:
    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(normalize_page(page.extract_text() or ""))
        except Exception as e:
            logger.warning("pdf page extraction failed: %r", e)
            pages.append("")
    return ExtractedText(pages=pages)


def is_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


async def extract_text(data: bytes) -> ExtractedText:
    if not is_pdf(data):
        return ExtractedText(pages=[])
    return await asyncio.to_thread(_extract, data)
