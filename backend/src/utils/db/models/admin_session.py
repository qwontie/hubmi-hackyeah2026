import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, uuid_pk


class AdminSession(SQLModel, table=True):
    __tablename__ = "admin_session"
    __table_args__ = (Index("ix_admin_session_expires_at", "expires_at"),)

    id: uuid.UUID = uuid_pk()
    admin_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("admin_user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    created_at: datetime = created_at_col()


__all__ = ["AdminSession"]
