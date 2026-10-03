import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Computed, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, updated_at_col, uuid_pk
from .innovation import EMBEDDING_DIMENSIONS
from .material import KnowledgeStatus, pg_enum, text_array

CHALLENGE_SEARCH_SQL = (
    "setweight(to_tsvector('simple'::regconfig,"
    " hubmi_unaccent(coalesce(title, ''))), 'A')"
    " || setweight(to_tsvector('simple'::regconfig, hubmi_unaccent("
    "coalesce(summary, '') || ' ' || coalesce(description, ''))), 'B')"
)


class Challenge(SQLModel, table=True):
    __tablename__ = "challenge"
    __table_args__ = (
        Index("ix_challenge_search", "search", postgresql_using="gin"),
        Index(
            "ix_challenge_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: uuid.UUID = uuid_pk()
    slug: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    area: str = Field(sa_column=Column(Text, nullable=False, index=True))
    position: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    title: str = Field(sa_column=Column(Text, nullable=False))
    summary: str = Field(default="", sa_column=Column(Text, nullable=False))
    description: str = Field(default="", sa_column=Column(Text, nullable=False))
    figures: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(
            postgresql.JSONB, nullable=False, server_default=text("'[]'::jsonb")
        ),
    )
    source_url: str = Field(sa_column=Column(Text, nullable=False))
    source_title: str = Field(default="", sa_column=Column(Text, nullable=False))
    source_pages: list[int] = Field(
        default_factory=list,
        sa_column=Column(
            postgresql.ARRAY(Integer), nullable=False, server_default=text("'{}'")
        ),
    )
    material_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("material.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    source_hash: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: KnowledgeStatus = Field(
        default=KnowledgeStatus.PUBLISHED,
        sa_column=Column(
            pg_enum(KnowledgeStatus, "knowledge_status"),
            nullable=False,
            server_default=KnowledgeStatus.PUBLISHED.value,
            index=True,
        ),
    )
    verified_at: datetime | None = nullable_ts_col()
    verified_by: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    imported_at: datetime | None = nullable_ts_col()
    edited_at: datetime | None = nullable_ts_col()
    edited_fields: list[str] = Field(default_factory=list, sa_column=text_array())
    embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    )
    embedded_hash: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    search: str | None = Field(
        default=None,
        sa_column=Column(
            postgresql.TSVECTOR, Computed(CHALLENGE_SEARCH_SQL, persisted=True)
        ),
    )
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = ["Challenge"]
