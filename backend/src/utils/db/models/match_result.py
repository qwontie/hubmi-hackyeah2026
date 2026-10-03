import uuid
from datetime import datetime

from sqlalchemy import Column, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, uuid_pk


class MatchResult(SQLModel, table=True):
    __tablename__ = "match_result"

    id: uuid.UUID = uuid_pk()
    need_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("need.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    innovation_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("innovation.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    rank: int = Field(sa_column=Column(Integer, nullable=False))
    score: float = Field(sa_column=Column(Float, nullable=False))
    reason: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = created_at_col()
