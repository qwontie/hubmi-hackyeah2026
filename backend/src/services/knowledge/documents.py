import asyncio
import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from pypdf import PdfReader

from services.ingest.fetch import RETRIES, PageFetcher
from utils.logging import logger

MAX_BYTES = 60 * 1024 * 1024
HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
SPACES = re.compile(r"[ \t ]+")
BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True, slots=True)
class Document:
    data: bytes
    sha256: str


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


async def remote_size(fetcher: PageFetcher, url: str) -> int | None:
    try:
        response = await fetcher.client.head(url)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("head %s failed: %r", url, e)
        return None
    finally:
        await asyncio.sleep(fetcher.delay / 2)
    length = response.headers.get("content-length")
    return int(length) if length and length.isdigit() else None


async def download(
    fetcher: PageFetcher, url: str, *, cache_dir: Path | None = None
) -> Document:
    cached = _cache_path(cache_dir, url)
    if cached is not None and cached.exists():
        data = cached.read_bytes()
        return Document(data=data, sha256=hashlib.sha256(data).hexdigest())
    last_error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            response = await fetcher.client.get(url)
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
        return Document(data=data, sha256=hashlib.sha256(data).hexdigest())
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
