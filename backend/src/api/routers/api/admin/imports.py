from typing import Annotated, Any

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import conflict
from api.security import AdminPerson
from services.dialogue.audit import record
from services.ingest import (
    ImportAlreadyRunningError,
    latest_runs,
    run_payload,
    start_import,
)
from utils.db.models import ImportTrigger

router = APIRouter(route_class=DishkaRoute)

RUNNING = "Import już trwa. Poczekaj na jego zakończenie."


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def run(admin: AdminPerson, session: FromDishka[AsyncSession]) -> dict[str, str]:
    try:
        started = await start_import(trigger=ImportTrigger.ADMIN)
    except ImportAlreadyRunningError as exc:
        raise conflict(RUNNING) from exc
    record(session, admin, "import.run", target=("import_run", started.id))
    await session.commit()
    return {"run_id": str(started.id)}


@router.get("/runs")
async def runs(
    session: FromDishka[AsyncSession], limit: Annotated[int, Query(ge=1, le=100)] = 20
) -> list[dict[str, Any]]:
    return [run_payload(item) for item in await latest_runs(session, limit)]
