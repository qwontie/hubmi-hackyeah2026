import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Integer, Text, text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, updated_at_col, uuid_pk
from .import_run import ImportStatus, ImportTrigger
from .material import pg_enum


class KnowledgeRun(SQLModel, table=True):
    __tablename__ = "knowledge_run"

    id: uuid.UUID = uuid_pk()
    status: ImportStatus = Field(
        default=ImportStatus.RUNNING,
        sa_column=Column(pg_enum(ImportStatus, "import_status"), nullable=False),
    )
    trigger: ImportTrigger = Field(
        sa_column=Column(pg_enum(ImportTrigger, "import_trigger"), nullable=False)
    )
    step: str = Field(default="", sa_column=Column(Text, nullable=False))
    done: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    total: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    counters: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            postgresql.JSONB, nullable=False, server_default=text("'{}'::jsonb")
        ),
    )
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    started_at: datetime = created_at_col()
    finished_at: datetime | None = nullable_ts_col()
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = ["KnowledgeRun"]
