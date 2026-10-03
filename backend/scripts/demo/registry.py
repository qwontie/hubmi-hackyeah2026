import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import DemoRecord

ADMIN = "admin_user"
NEED = "need"
CLUSTER = "need_cluster"
MESSAGE = "message"
FEEDBACK = "feedback"
SIGNUP = "test_signup"
IDEA = "idea"
ADAPTATION = "adaptation"
DEMAND = "innovation_demand"
ASSIGNMENT = "assignment"
KINDS = (
    ADMIN,
    NEED,
    CLUSTER,
    MESSAGE,
    FEEDBACK,
    SIGNUP,
    IDEA,
    ADAPTATION,
    DEMAND,
    ASSIGNMENT,
)


async def register(
    session: AsyncSession, kind: str, key: str, row_id: uuid.UUID
) -> None:
    session.add(DemoRecord(kind=kind, key=key, row_id=row_id))
    await session.commit()


async def lookup(session: AsyncSession, kind: str, key: str) -> uuid.UUID | None:
    return (
        await session.exec(
            select(DemoRecord.row_id).where(
                col(DemoRecord.kind) == kind, col(DemoRecord.key) == key
            )
        )
    ).first()


async def row_ids(session: AsyncSession, kind: str) -> list[uuid.UUID]:
    return list(
        (
            await session.exec(
                select(DemoRecord.row_id).where(col(DemoRecord.kind) == kind)
            )
        ).all()
    )


async def counts(session: AsyncSession) -> dict[str, int]:
    rows = await session.exec(
        select(DemoRecord.kind, func.count()).group_by(col(DemoRecord.kind))
    )
    found = dict(rows.all())
    return {kind: int(found.get(kind, 0)) for kind in KINDS}
