import uuid
from datetime import datetime

from sqlalchemy import Column, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, uuid_pk


class DemoRecord(SQLModel, table=True):
    __tablename__ = "demo_record"
    __table_args__ = (UniqueConstraint("kind", "key", name="uq_demo_record_kind_key"),)

    id: uuid.UUID = uuid_pk()
    kind: str = Field(sa_column=Column(Text, nullable=False, index=True))
    key: str = Field(sa_column=Column(Text, nullable=False))
    row_id: uuid.UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), nullable=False, index=True)
    )
    created_at: datetime = created_at_col()


__all__ = ["DemoRecord"]
