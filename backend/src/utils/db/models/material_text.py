import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, updated_at_col
from .material import text_array


class MaterialText(SQLModel, table=True):
    __tablename__ = "material_text"

    material_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("material.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    pages: list[str] = Field(default_factory=list, sa_column=text_array())
    chars: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = ["MaterialText"]
