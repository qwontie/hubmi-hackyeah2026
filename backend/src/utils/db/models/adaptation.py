import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, ForeignKey, Index, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, uuid_pk


class Adaptation(SQLModel, table=True):
    __tablename__ = "adaptation"
    __table_args__ = (Index("ix_adaptation_created_at", "created_at"),)

    id: uuid.UUID = uuid_pk()
    innovation_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("innovation.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    institution_type: str = Field(sa_column=Column(Text, nullable=False, index=True))
    place: str = Field(sa_column=Column(Text, nullable=False))
    powiat: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True, index=True)
    )
    context: str = Field(sa_column=Column(Text, nullable=False))
    plan: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(postgresql.JSONB, nullable=False)
    )
    model: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = created_at_col()


__all__ = ["Adaptation"]
