import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, LargeBinary, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col


class MaterialFile(SQLModel, table=True):
    __tablename__ = "material_file"

    material_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("material.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    mime_type: str = Field(sa_column=Column(Text, nullable=False))
    filename: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = created_at_col()


__all__ = ["MaterialFile"]
