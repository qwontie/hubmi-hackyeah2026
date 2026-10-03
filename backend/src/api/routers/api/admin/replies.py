import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from api.routers.api.modules.common import ai_guard
from services.dialogue import inbox
from services.replies import ReplySuggestions, suggest

router = APIRouter(route_class=DishkaRoute)

suggest_limit = rate_limit("admin_reply_suggestions", per_minute=20, per_day=500)

NEED_MISSING = "Nie znaleziono zgłoszenia."


@router.post("/{need_id}/reply-suggestions", dependencies=[Depends(suggest_limit)])
async def reply_suggestions(
    need_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> ReplySuggestions:
    need = await inbox.get_need(session, need_id)
    if need is None:
        raise not_found(NEED_MISSING)
    async with ai_guard():
        return await suggest(session, need)
