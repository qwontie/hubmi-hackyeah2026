import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, Text
from sqlmodel import Field, SQLModel

from .base import created_at_col, updated_at_col, uuid_pk


class Category(SQLModel, table=True):
    __tablename__ = "category"

    id: uuid.UUID = uuid_pk()
    slug: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    name: str = Field(sa_column=Column(Text, nullable=False))
    source_url: str = Field(sa_column=Column(Text, nullable=False))
    icon_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    position: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()
