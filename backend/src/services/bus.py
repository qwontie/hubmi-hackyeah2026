import asyncio
import contextlib
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Message:
    topic: str
    data: Any
    event_id: str | None = None


@dataclass(slots=True)
class Bus:
    queues: set[asyncio.Queue[Message]] = field(default_factory=set)
    limit: int = 1000

    def publish(self, topic: str, data: Any, *, event_id: str | None = None) -> None:  # noqa: ANN401
        message = Message(topic=topic, data=data, event_id=event_id)
        for queue in list(self.queues):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            queue.put_nowait(message)

    @contextlib.asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[asyncio.Queue[Message]]:
        queue: asyncio.Queue[Message] = asyncio.Queue(maxsize=self.limit)
        self.queues.add(queue)
        try:
            yield queue
        finally:
            self.queues.discard(queue)


bus = Bus()
