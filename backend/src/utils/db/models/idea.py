import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, Enum, Identity, Index, Integer, Text, text
from sqlalchemy import false as sa_false
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, updated_at_col, uuid_pk
from .innovation import EMBEDDING_DIMENSIONS


class IdeaStage(StrEnum):
    IDEA = "idea"
    PREPARING = "preparing"
    TESTING = "testing"
    RUNNING = "running"


class IdeaStatus(StrEnum):
    NEW = "new"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


def _enum[T: StrEnum](enum: type[T], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda e: [m.value for m in e])


class Idea(SQLModel, table=True):
    __tablename__ = "idea"
    __table_args__ = (
        Index(
            "ix_idea_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_idea_created_at", "created_at"),
    )

    id: uuid.UUID = uuid_pk()
    number: int | None = Field(
        default=None, sa_column=Column(Integer, Identity(), nullable=False, unique=True)
    )
    title: str = Field(sa_column=Column(Text, nullable=False))
    essence: str = Field(sa_column=Column(Text, nullable=False))
    for_whom: str = Field(sa_column=Column(Text, nullable=False))
    stage: IdeaStage = Field(
        sa_column=Column(_enum(IdeaStage, "idea_stage"), nullable=False, index=True)
    )
    canvas: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            postgresql.JSONB, nullable=False, server_default=text("'{}'::jsonb")
        ),
    )
    powiat: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True, index=True)
    )
    contact_email: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    contact_consent: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=sa_false()),
    )
    consent_at: datetime | None = nullable_ts_col()
    status: IdeaStatus = Field(
        default=IdeaStatus.NEW,
        sa_column=Column(
            _enum(IdeaStatus, "idea_status"),
            nullable=False,
            server_default=IdeaStatus.NEW.value,
            index=True,
        ),
    )
    edit_token_hash: str = Field(sa_column=Column(Text, nullable=False))
    embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    )
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = ["Idea", "IdeaStage", "IdeaStatus"]
