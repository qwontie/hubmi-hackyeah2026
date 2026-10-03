import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, Enum, ForeignKey, Integer, LargeBinary, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col


class ImageSource(StrEnum):
    ROPS = "rops"
    YOUTUBE = "youtube"
    GENERATED = "generated"


class InnovationImage(SQLModel, table=True):
    __tablename__ = "innovation_image"

    innovation_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("innovation.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    version: int = Field(sa_column=Column(Integer, nullable=False))
    source: ImageSource = Field(
        sa_column=Column(
            Enum(
                ImageSource,
                name="image_source",
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    source_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    image: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    card: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    mime_type: str = Field(sa_column=Column(Text, nullable=False))
    width: int = Field(sa_column=Column(Integer, nullable=False))
    height: int = Field(sa_column=Column(Integer, nullable=False))
    alt: str = Field(sa_column=Column(Text, nullable=False))
    prompt: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    model: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = created_at_col()


__all__ = ["ImageSource", "InnovationImage"]
