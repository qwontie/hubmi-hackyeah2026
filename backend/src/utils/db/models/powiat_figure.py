import uuid
from datetime import datetime

from sqlalchemy import Column, Float, Integer, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from .base import created_at_col, updated_at_col, uuid_pk


class PowiatFigure(SQLModel, table=True):
    __tablename__ = "powiat_figure"
    __table_args__ = (
        UniqueConstraint("powiat", "key", "year", name="uq_powiat_figure"),
    )

    id: uuid.UUID = uuid_pk()
    powiat: str = Field(sa_column=Column(Text, nullable=False, index=True))
    key: str = Field(sa_column=Column(Text, nullable=False))
    label: str = Field(sa_column=Column(Text, nullable=False))
    value: float = Field(sa_column=Column(Float, nullable=False))
    unit: str = Field(default="", sa_column=Column(Text, nullable=False))
    year: int = Field(sa_column=Column(Integer, nullable=False))
    source_url: str = Field(sa_column=Column(Text, nullable=False))
    source_title: str = Field(default="", sa_column=Column(Text, nullable=False))
    page: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = ["PowiatFigure"]
