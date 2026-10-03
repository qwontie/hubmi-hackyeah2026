import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, ForeignKey, Index, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, jsonb_column, uuid_pk


class AdminAction(SQLModel, table=True):
    __tablename__ = "admin_action"
    __table_args__ = (
        Index("ix_admin_action_created_at", "created_at"),
        Index("ix_admin_action_target", "target_type", "target_id"),
    )

    id: uuid.UUID = uuid_pk()
    admin_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("admin_user.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    admin_login: str = Field(sa_column=Column(Text, nullable=False))
    action: str = Field(sa_column=Column(Text, nullable=False))
    target_type: str = Field(sa_column=Column(Text, nullable=False))
    target_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    details: dict[str, Any] = Field(
        default_factory=dict, sa_column=jsonb_column(default="{}")
    )
    created_at: datetime = created_at_col()


__all__ = ["AdminAction"]
