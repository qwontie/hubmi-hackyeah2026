from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from services.bus import Message, bus
from services.dialogue.links import admin_idea_url, admin_need_url
from utils.env import env
from utils.logging import logger

from .staff import StaffNotifier
from .templates import StaffItem, StaffItemKind

NEED_TOPICS = frozenset({"need.created", "need.updated"})
MODULE_TOPICS = frozenset(
    {"volunteer.created", "volunteer.reported", "assignment.answered"}
)


def admin_application_url(application_id: str) -> str:
    base = env.mailer.public_url.rstrip("/")
    return f"{base}/admin/applications/{application_id}"


def admin_volunteer_url(signup_id: str) -> str:
    base = env.mailer.public_url.rstrip("/")
    return f"{base}/admin/volunteers/{signup_id}"


def volunteer_item(topic: str, data: Mapping[str, Any]) -> StaffItem | None:
    innovation = (data.get("innovation") or {}).get("title", "")
    if topic == "volunteer.created":
        return StaffItem(
            kind=StaffItemKind.VOLUNTEER,
            key=f"volunteer:{data['id']}",
            text=f"{innovation}: {data.get('proposal', '')}",
            url=admin_volunteer_url(data["id"]),
        )
    report = data.get("report") or {}
    if topic == "volunteer.reported" and report.get("created_at") == report.get(
        "updated_at"
    ):
        return StaffItem(
            kind=StaffItemKind.VOLUNTEER_REPORT,
            key=f"volunteer-report:{data['id']}",
            text=f"{innovation}: {report.get('activity', '')}",
            url=admin_volunteer_url(data["id"]),
        )
    return None


def module_item(topic: str, data: Mapping[str, Any]) -> StaffItem | None:
    if topic != "assignment.answered":
        return volunteer_item(topic, data)
    if not (data.get("expert") or {}).get("email"):
        return None
    idea_id = data.get("idea_id")
    return StaffItem(
        kind=StaffItemKind.EXPERT_ANSWER,
        key=f"expert-answer:{data['id']}:{data.get('opinions_count')}",
        text=str(data.get("title", "")),
        url=admin_idea_url(idea_id) if idea_id else admin_need_url(data["need_id"]),
    )


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
    if message.topic == "application.submitted" and "id" in data:
        idea = data.get("idea") or {}
        return StaffItem(
            kind=StaffItemKind.APPLICATION,
            key=f"application:{data['id']}",
            text=f"Wniosek nr {data.get('number')}: {idea.get('title', '')}",
            url=admin_application_url(data["id"]),
        )
    if message.topic in MODULE_TOPICS and "id" in data:
        return module_item(message.topic, data)
    if message.topic == "message.created" and data.get("direction") == "from_author":
        idea_id = data.get("idea_id")
        return StaffItem(
            kind=StaffItemKind.IDEA_MESSAGE
            if idea_id
            else StaffItemKind.AUTHOR_MESSAGE,
            key=f"message:{data['id']}",
            text=str(data.get("body", "")),
            url=admin_idea_url(idea_id) if idea_id else admin_need_url(data["need_id"]),
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
