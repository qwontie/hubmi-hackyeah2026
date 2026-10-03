from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import DemoRecord

router = APIRouter(route_class=DishkaRoute)


@router.get("")
async def meta(session: FromDishka[AsyncSession]) -> dict[str, bool]:
    count = await session.exec(select(func.count()).select_from(DemoRecord))
    return {"demo": int(count.one()) > 0}
