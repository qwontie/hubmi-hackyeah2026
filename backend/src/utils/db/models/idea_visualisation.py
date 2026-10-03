import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, LargeBinary, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col


class IdeaVisualisation(SQLModel, table=True):
    __tablename__ = "idea_visualisation"

    idea_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("idea.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    version: int = Field(sa_column=Column(Integer, nullable=False))
    image: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    mime_type: str = Field(sa_column=Column(Text, nullable=False))
    prompt: str = Field(sa_column=Column(Text, nullable=False))
    alt: str = Field(sa_column=Column(Text, nullable=False))
    model: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = created_at_col()


__all__ = ["IdeaVisualisation"]
