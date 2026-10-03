import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, Float, Index, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, uuid_pk


class SearchLog(SQLModel, table=True):
    __tablename__ = "search_log"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('ok', 'unclear', 'no_match')", name="ck_search_log_outcome"
        ),
        Index("ix_search_log_created_at", "created_at"),
    )

    id: uuid.UUID = uuid_pk()
    outcome: str = Field(sa_column=Column(Text, nullable=False))
    category_slug: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    slugs: list[str] = Field(
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(Text), nullable=False, server_default="{}"),
    )
    scores: list[float] = Field(
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(Float), nullable=False, server_default="{}"),
    )
    degraded: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))
    created_at: datetime = created_at_col()
