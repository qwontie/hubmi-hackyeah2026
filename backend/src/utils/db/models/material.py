import uuid
from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Column, Computed, Enum, Index, Integer, Text, text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, updated_at_col, uuid_pk
from .innovation import EMBEDDING_DIMENSIONS

MATERIAL_SEARCH_SQL = (
    "setweight(to_tsvector('simple'::regconfig,"
    " hubmi_unaccent(coalesce(title, ''))), 'A')"
    " || setweight(to_tsvector('simple'::regconfig,"
    " hubmi_unaccent(coalesce(summary, ''))), 'B')"
)


class MaterialKind(StrEnum):
    REPORT = "report"
    PUBLICATION = "publication"
    GUIDE = "guide"
    VIDEO = "video"


class KnowledgeStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class SummaryState(StrEnum):
    PENDING = "pending"
    DONE = "done"
    NO_TEXT = "no_text"
    FAILED = "failed"


def pg_enum[T: StrEnum](enum: type[T], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda e: [m.value for m in e])


def text_array() -> Column:
    return Column(postgresql.ARRAY(Text), nullable=False, server_default=text("'{}'"))


class Material(SQLModel, table=True):
    __tablename__ = "material"
    __table_args__ = (
        Index("ix_material_search", "search", postgresql_using="gin"),
        Index("ix_material_topics", "topics", postgresql_using="gin"),
        Index(
            "ix_material_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: uuid.UUID = uuid_pk()
    kind: MaterialKind = Field(
        sa_column=Column(
            pg_enum(MaterialKind, "material_kind"), nullable=False, index=True
        )
    )
    title: str = Field(sa_column=Column(Text, nullable=False))
    year: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True, index=True)
    )
    summary: str = Field(default="", sa_column=Column(Text, nullable=False))
    topics: list[str] = Field(default_factory=list, sa_column=text_array())
    file_url: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    source_url: str = Field(sa_column=Column(Text, nullable=False))
    source_section: str = Field(default="", sa_column=Column(Text, nullable=False))
    file_size: int | None = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    pages: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    source_hash: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    summary_state: SummaryState = Field(
        default=SummaryState.PENDING,
        sa_column=Column(
            pg_enum(SummaryState, "summary_state"),
            nullable=False,
            server_default=SummaryState.PENDING.value,
        ),
    )
    summary_hash: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    status: KnowledgeStatus = Field(
        default=KnowledgeStatus.PUBLISHED,
        sa_column=Column(
            pg_enum(KnowledgeStatus, "knowledge_status"),
            nullable=False,
            server_default=KnowledgeStatus.PUBLISHED.value,
            index=True,
        ),
    )
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
            postgresql.TSVECTOR, Computed(MATERIAL_SEARCH_SQL, persisted=True)
        ),
    )
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = [
    "KnowledgeStatus",
    "Material",
    "MaterialKind",
    "SummaryState",
    "pg_enum",
    "text_array",
]
