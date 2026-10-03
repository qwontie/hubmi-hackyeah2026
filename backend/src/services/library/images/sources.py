import io
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx
from PIL import Image, ImageStat
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from services.ingest.fetch import USER_AGENT
from utils.logging import logger

from .pictures import UnusableImageError, load

PDF_LIMIT_BYTES = 40 * 1024 * 1024
PDF_PAGES = 4
MIN_WIDTH = 400
MIN_HEIGHT = 250
MIN_RATIO = 0.5
MAX_RATIO = 2.6
CANDIDATES = 3
THUMBNAILS = ("maxresdefault", "sddefault", "hqdefault")
PLACEHOLDER_WIDTH = 120
MIN_SATURATION = 18.0
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


@dataclass(frozen=True, slots=True)
class Candidate:
    data: bytes
    source_url: str
    width: int
    height: int


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "pl"},
        timeout=httpx.Timeout(60.0),
        follow_redirects=True,
    )


def video_id(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").removeprefix("www.").removeprefix("m.")
    found: str | None = None
    if host == "youtu.be":
        found = parsed.path.strip("/").split("/")[0]
    elif host.endswith(("youtube.com", "youtube-nocookie.com")):
        if parsed.path == "/watch":
            found = (parse_qs(parsed.query).get("v") or [None])[0]
        else:
            prefix, _, rest = parsed.path.strip("/").partition("/")
            if prefix in {"embed", "shorts", "v", "live"}:
                found = rest.split("/")[0]
    return found if found and VIDEO_ID.match(found) else None


async def download(http: httpx.AsyncClient, url: str, limit: int) -> bytes | None:
    try:
        async with http.stream("GET", url) as response:
            if response.status_code != httpx.codes.OK:
                return None
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > limit:
                    logger.warning("image source %s is over %d bytes", url, limit)
                    return None
                chunks.append(chunk)
            return b"".join(chunks)
    except httpx.HTTPError as e:
        logger.warning("image source %s failed: %r", url, e)
        return None


def fits(width: int, height: int) -> bool:
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        return False
    return MIN_RATIO <= width / height <= MAX_RATIO


def pdf_pictures(data: bytes, source_url: str) -> list[Candidate]:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = list(reader.pages[:PDF_PAGES])
    except (PdfReadError, ValueError, OSError) as e:
        logger.warning("brochure %s unreadable: %r", source_url, e)
        return []
    found: list[Candidate] = []
    seen: set[int] = set()
    for page in pages:
        try:
            images = list(page.images)
        except Exception as e:
            logger.warning("brochure %s page images failed: %r", source_url, e)
            continue
        for image in images:
            raw = image.data
            if hash(raw) in seen:
                continue
            seen.add(hash(raw))
            try:
                picture = load(raw)
            except UnusableImageError:
                continue
            if not fits(*picture.size) or is_grayscale(picture):
                continue
            found.append(Candidate(raw, source_url, *picture.size))
    found.sort(key=lambda c: c.width * c.height, reverse=True)
    return found[:CANDIDATES]


def is_grayscale(picture: Image.Image) -> bool:
    saturation = ImageStat.Stat(picture.convert("HSV").resize((32, 24))).mean[1]
    return saturation < MIN_SATURATION


async def brochure_candidates(
    http: httpx.AsyncClient, url: str | None
) -> list[Candidate]:
    if not url or not url.lower().split("?")[0].endswith(".pdf"):
        return []
    data = await download(http, url, PDF_LIMIT_BYTES)
    if data is None:
        return []
    return pdf_pictures(data, url)


async def youtube_candidate(
    http: httpx.AsyncClient, url: str | None
) -> Candidate | None:
    found = video_id(url)
    if found is None:
        return None
    for name in THUMBNAILS:
        thumbnail = f"https://i.ytimg.com/vi/{found}/{name}.jpg"
        data = await download(http, thumbnail, 5 * 1024 * 1024)
        if data is None:
            continue
        try:
            picture = load(data)
        except UnusableImageError:
            continue
        if picture.width <= PLACEHOLDER_WIDTH:
            continue
        return Candidate(data, thumbnail, *picture.size)
    return None
