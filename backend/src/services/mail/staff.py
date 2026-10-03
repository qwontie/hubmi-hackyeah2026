import asyncio
import time
from collections import deque

from utils.env import MailSettings
from utils.logging import logger

from .sender import Mailer
from .templates import StaffItem, staff_digest

SEEN_LIMIT = 2000


class StaffNotifier:
    def __init__(self, mailer: Mailer, settings: MailSettings, inbox_url: str) -> None:
        self._mailer = mailer
        self._settings = settings
        self._inbox_url = inbox_url
        self._pending: list[StaffItem] = []
        self._seen: deque[str] = deque(maxlen=SEEN_LIMIT)
        self._last_sent = float("-inf")
        self._task: asyncio.Task[None] | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._settings.staff_email)

    def push(self, item: StaffItem) -> None:
        if not self.enabled or item.key in self._seen:
            return
        self._seen.append(item.key)
        self._pending.append(item)
        if self._task is None or self._task.done():
            delay = max(
                0.0,
                self._last_sent
                + self._settings.staff_digest_seconds
                - time.monotonic(),
            )
            self._task = asyncio.create_task(self._flush_after(delay))

    async def _flush_after(self, delay: float) -> None:
        await asyncio.sleep(delay)
        await self.flush()

    async def flush(self) -> None:
        if not self._pending or not self._settings.staff_email:
            return
        items, self._pending = self._pending, []
        self._last_sent = time.monotonic()
        try:
            await self._mailer.send(
                staff_digest(
                    to=self._settings.staff_email,
                    items=items,
                    inbox_url=self._inbox_url,
                )
            )
        except Exception:
            logger.exception("staff digest failed")

    async def close(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
        await self.flush()
