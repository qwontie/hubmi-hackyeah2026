import uuid
from datetime import datetime
from typing import Annotated, Any

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlmodel import col
from sqlmodel import select as entity_select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import AdminAction

router = APIRouter(route_class=DishkaRoute)


class AuditEntry(BaseModel):
    id: uuid.UUID
    admin_login: str
    action: str
    target_type: str
    target_id: str | None
    details: dict[str, Any]
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditEntry]
    total: int
    page: int
    per_page: int


class AuditQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: str | None = Field(default=None, max_length=50)
    target_id: str | None = Field(default=None, max_length=200)
    admin: str | None = Field(default=None, max_length=100)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=100)


@router.get("")
async def audit(
    query: Annotated[AuditQuery, Query()], session: FromDishka[AsyncSession]
) -> AuditPage:
    where = []
    if query.target_type:
        where.append(col(AdminAction.target_type) == query.target_type)
    if query.target_id:
        where.append(col(AdminAction.target_id) == query.target_id)
    if query.admin:
        where.append(col(AdminAction.admin_login) == query.admin)
    total = await session.scalar(
        select(func.count()).select_from(AdminAction).where(*where)
    )
    result = await session.exec(
        entity_select(AdminAction)
        .where(*where)
        .order_by(col(AdminAction.created_at).desc(), col(AdminAction.id))
        .offset((query.page - 1) * query.per_page)
        .limit(query.per_page)
    )
    items = [
        AuditEntry.model_validate(entry, from_attributes=True) for entry in result.all()
    ]
    return AuditPage(
        items=items, total=int(total or 0), page=query.page, per_page=query.per_page
    )
