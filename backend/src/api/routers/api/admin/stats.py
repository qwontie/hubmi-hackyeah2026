from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter
from sqlmodel.ext.asyncio.session import AsyncSession

from services.needs import POWIATS
from services.stats.queries import collect
from services.stats.schemas import Period, Stats

router = APIRouter(route_class=DishkaRoute)


@router.get("")
async def stats(
    session: FromDishka[AsyncSession], period: Period = Period.MONTH
) -> Stats:
    return await collect(session, period, POWIATS)
