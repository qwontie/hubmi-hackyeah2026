import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic_core import to_json

from api.security import AdminPerson
from services.bus import Message, bus
from utils.logging import logger

router = APIRouter()

PING_SECONDS = 15.0
HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def frame(message: Message) -> str:
    try:
        data = to_json(message.data).decode()
    except Exception:
        logger.exception("stream: cannot encode %s", message.topic)
        return ""
    head = f"id: {message.event_id}\n" if message.event_id else ""
    return f"{head}event: {message.topic}\ndata: {data}\n\n"


async def events() -> AsyncGenerator[str]:
    async with bus.subscribe() as queue:
        yield "retry: 3000\n\n"
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), PING_SECONDS)
            except TimeoutError:
                yield ": ping\n\n"
                continue
            text = frame(message)
            if text:
                yield text


@router.get("")
async def stream(_admin: AdminPerson) -> StreamingResponse:
    return StreamingResponse(events(), media_type="text/event-stream", headers=HEADERS)
