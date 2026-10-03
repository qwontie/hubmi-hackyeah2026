import uuid
from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Computed, Enum, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, updated_at_col, uuid_pk

EMBEDDING_DIMENSIONS = 768


def _weighted(columns: tuple[str, ...], weight: str) -> str:
    joined = " || ' ' || ".join(f"coalesce({c}, '')" for c in columns)
    return (
        f"setweight(to_tsvector('simple'::regconfig, hubmi_unaccent({joined})), "
        f"'{weight}')"
    )


INNOVATION_SEARCH_SQL = " || ".join(
    (
        _weighted(("title",), "A"),
        _weighted(("lead",), "B"),
        _weighted(("problems", "target_group"), "B"),
        _weighted(("what_it_is", "who_can_use", "effectiveness"), "C"),
    )
)


class InnovationStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Innovation(SQLModel, table=True):
    __tablename__ = "innovation"
    __table_args__ = (
        Index("ix_innovation_search", "search", postgresql_using="gin"),
        Index(
            "ix_innovation_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: uuid.UUID = uuid_pk()
    slug: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    category_slug: str = Field(
        sa_column=Column(
            Text,
            ForeignKey("category.slug", onupdate="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    title: str = Field(sa_column=Column(Text, nullable=False))
    lead: str = Field(default="", sa_column=Column(Text, nullable=False))
    what_it_is: str = Field(default="", sa_column=Column(Text, nullable=False))
    problems: str = Field(default="", sa_column=Column(Text, nullable=False))
    target_group: str = Field(default="", sa_column=Column(Text, nullable=False))
    who_can_use: str = Field(default="", sa_column=Column(Text, nullable=False))
    effectiveness: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    authors: list[str] = Field(
        default_factory=list,
        sa_column=Column(
            postgresql.ARRAY(Text), nullable=False, server_default=text("'{}'")
        ),
    )
    qr_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    video_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    materials_url: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    brochure_url: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    license: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    image_version: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    image_source: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    image_alt: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: InnovationStatus = Field(
        default=InnovationStatus.PUBLISHED,
        sa_column=Column(
            Enum(
                InnovationStatus,
                name="innovation_status",
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
            server_default=InnovationStatus.PUBLISHED.value,
            index=True,
        ),
    )
    source_url: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True, unique=True)
    )
    source_hash: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    imported_at: datetime | None = nullable_ts_col()
    edited_at: datetime | None = nullable_ts_col()
    edited_fields: list[str] = Field(
        default_factory=list,
        sa_column=Column(
            postgresql.ARRAY(Text), nullable=False, server_default=text("'{}'")
        ),
    )
    embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    )
    embedded_hash: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    search: str | None = Field(
        default=None,
        sa_column=Column(
            postgresql.TSVECTOR, Computed(INNOVATION_SEARCH_SQL, persisted=True)
        ),
    )
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = ["EMBEDDING_DIMENSIONS", "Innovation", "InnovationStatus"]
