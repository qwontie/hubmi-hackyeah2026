from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(tags=["health"], route_class=DishkaRoute)


@router.get("")
@router.get("/")
async def health(session: FromDishka[AsyncSession]) -> dict[str, bool]:
    result = await session.scalars(text("SELECT 1"))
    return {"db": result.first() == 1}
