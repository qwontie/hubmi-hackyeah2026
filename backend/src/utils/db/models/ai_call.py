import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Index, Integer, Numeric, Text
from sqlmodel import Field, SQLModel

from .base import created_at_col, uuid_pk


class AiCall(SQLModel, table=True):
    __tablename__ = "ai_call"
    __table_args__ = (Index("ix_ai_call_created_at", "created_at"),)

    id: uuid.UUID = uuid_pk()
    kind: str = Field(sa_column=Column(Text, nullable=False, index=True))
    model: str = Field(sa_column=Column(Text, nullable=False))
    input_tokens: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    output_tokens: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    cost_usd: float = Field(
        default=0, sa_column=Column(Numeric(12, 6, asdecimal=False), nullable=False)
    )
    latency_ms: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    ok: bool = Field(default=True, sa_column=Column(Boolean, nullable=False))
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = created_at_col()
