from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from services.bus import Message, bus
from services.dialogue.links import admin_idea_url, admin_need_url
from utils.logging import logger

from .staff import StaffNotifier
from .templates import StaffItem, StaffItemKind

NEED_TOPICS = frozenset({"need.created", "need.updated"})


def payload(data: object) -> Mapping[str, Any]:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, Mapping):
        return data
    return {}


def staff_item(message: Message) -> StaffItem | None:
    data = payload(message.data)
    if message.topic in NEED_TOPICS and data.get("status", "new") == "new":
        kind = None
        if data.get("nothing_fits"):
            kind = StaffItemKind.NOTHING_FITS
        elif message.topic == "need.created" and data.get("origin") == "form":
            kind = StaffItemKind.FORM_NEED
        if kind is not None:
            return StaffItem(
                kind=kind,
                key=f"need:{data['id']}",
                text=str(data.get("text", "")),
                url=admin_need_url(data["id"]),
            )
    if message.topic == "idea.created" and "id" in data:
        return StaffItem(
            kind=StaffItemKind.IDEA,
            key=f"idea:{data['id']}",
            text=str(data.get("title") or data.get("essence") or ""),
            url=admin_idea_url(data["id"]),
        )
    if message.topic == "message.created" and data.get("direction") == "from_author":
        return StaffItem(
            kind=StaffItemKind.AUTHOR_MESSAGE,
            key=f"message:{data['id']}",
            text=str(data.get("body", "")),
            url=admin_need_url(data["need_id"]),
        )
    return None


async def watch(notifier: StaffNotifier) -> None:
    async with bus.subscribe() as queue:
        while True:
            message = await queue.get()
            try:
                item = staff_item(message)
            except (KeyError, TypeError, ValueError):
                logger.exception("staff watch: bad %s payload", message.topic)
                continue
            if item is not None:
                notifier.push(item)
