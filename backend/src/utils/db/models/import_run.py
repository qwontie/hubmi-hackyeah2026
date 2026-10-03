import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, Enum, Integer, Text
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, updated_at_col, uuid_pk


class ImportStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ImportTrigger(StrEnum):
    SCRIPT = "script"
    ADMIN = "admin"
    SCHEDULE = "schedule"


def _count() -> int:
    return Field(default=0, sa_column=Column(Integer, nullable=False))


class ImportRun(SQLModel, table=True):
    __tablename__ = "import_run"

    id: uuid.UUID = uuid_pk()
    status: ImportStatus = Field(
        default=ImportStatus.RUNNING,
        sa_column=Column(
            Enum(
                ImportStatus,
                name="import_status",
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        ),
    )
    trigger: ImportTrigger = Field(
        sa_column=Column(
            Enum(
                ImportTrigger,
                name="import_trigger",
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    started_at: datetime = created_at_col()
    finished_at: datetime | None = nullable_ts_col()
    total: int = _count()
    created: int = _count()
    updated: int = _count()
    unchanged: int = _count()
    skipped_edited: int = _count()
    failed: int = _count()
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()
