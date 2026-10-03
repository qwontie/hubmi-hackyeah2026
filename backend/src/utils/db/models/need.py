import uuid
from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Identity, Index, Integer, Text
from sqlalchemy import false as sa_false
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, updated_at_col, uuid_pk
from .innovation import EMBEDDING_DIMENSIONS


class NeedOrigin(StrEnum):
    MATCH = "match"
    FORM = "form"


class NeedStatus(StrEnum):
    NEW = "new"
    ANSWERED = "answered"
    CLOSED = "closed"


def _enum[T: StrEnum](enum: type[T], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda e: [m.value for m in e])


class NeedCluster(SQLModel, table=True):
    __tablename__ = "need_cluster"
    __table_args__ = (
        Index(
            "ix_need_cluster_centroid",
            "centroid",
            postgresql_using="hnsw",
            postgresql_ops={"centroid": "vector_cosine_ops"},
        ),
    )

    id: uuid.UUID = uuid_pk()
    title: str = Field(sa_column=Column(Text, nullable=False))
    summary: str = Field(default="", sa_column=Column(Text, nullable=False))
    category_slug: str | None = Field(
        default=None,
        sa_column=Column(
            Text,
            ForeignKey("category.slug", onupdate="CASCADE", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    size: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    centroid: list[float] | None = Field(
        default=None, sa_column=Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    )
    last_need_at: datetime | None = nullable_ts_col()
    summary_size: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    summary_stale: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=sa_false()),
    )
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


class Need(SQLModel, table=True):
    __tablename__ = "need"
    __table_args__ = (
        Index(
            "ix_need_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_need_created_at", "created_at"),
    )

    id: uuid.UUID = uuid_pk()
    number: int | None = Field(
        default=None, sa_column=Column(Integer, Identity(), nullable=False, unique=True)
    )
    text: str = Field(sa_column=Column(Text, nullable=False))
    title: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    origin: NeedOrigin = Field(
        sa_column=Column(_enum(NeedOrigin, "need_origin"), nullable=False)
    )
    powiat: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True, index=True)
    )
    category_slug: str | None = Field(
        default=None,
        sa_column=Column(
            Text,
            ForeignKey("category.slug", onupdate="CASCADE", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    contact_email: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    contact_consent: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=sa_false()),
    )
    consent_at: datetime | None = nullable_ts_col()
    nothing_fits: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=sa_false()),
    )
    status: NeedStatus = Field(
        default=NeedStatus.NEW,
        sa_column=Column(
            _enum(NeedStatus, "need_status"),
            nullable=False,
            server_default=NeedStatus.NEW.value,
            index=True,
        ),
    )
    cluster_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("need_cluster.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    edit_token_hash: str = Field(sa_column=Column(Text, nullable=False))
    embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    )
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = ["Need", "NeedCluster", "NeedOrigin", "NeedStatus"]
