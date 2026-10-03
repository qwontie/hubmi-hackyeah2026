import asyncio
import hashlib
from pathlib import Path
from types import TracebackType
from typing import Self

import httpx

from utils.logging import logger

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0 Safari/537.36 HubMi-importer"
)
RETRIES = 3


class PageFetcher:
    def __init__(self, *, delay: float = 1.0, cache_dir: Path | None = None) -> None:
        self.delay = delay
        self.cache_dir = cache_dir
        self.client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "pl"},
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.client.aclose()

    def _cache_path(self, url: str) -> Path | None:
        if self.cache_dir is None:
            return None
        return self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()[:32]}.html"

    async def get(self, url: str) -> str:
        cached = self._cache_path(url)
        if cached is not None and cached.exists():
            return cached.read_text(encoding="utf-8")
        last_error: Exception | None = None
        for attempt in range(RETRIES):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
            except httpx.HTTPError as e:
                last_error = e
                logger.warning("fetch %s failed (%d): %r", url, attempt + 1, e)
                await asyncio.sleep(self.delay * (attempt + 2))
                continue
            await asyncio.sleep(self.delay)
            if cached is not None:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_text(response.text, encoding="utf-8")
            return response.text
        msg = f"cannot fetch {url}"
        raise RuntimeError(msg) from last_error
