from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(tags=["health"], route_class=DishkaRoute)


@router.get("")
@router.get("/")
async def health(
    session: FromDishka[AsyncSession], response: Response
) -> dict[str, bool]:
    try:
        result = await session.scalars(text("SELECT 1"))
        ok = result.first() == 1
    except Exception:
        ok = False
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"ok": ok}
