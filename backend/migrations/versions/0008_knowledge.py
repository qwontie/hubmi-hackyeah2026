"""knowledge: materials, challenges, powiat figures, import runs

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-03 16:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DIM = 768

MATERIAL_SEARCH_SQL = (
    "setweight(to_tsvector('simple'::regconfig,"
    " hubmi_unaccent(coalesce(title, ''))), 'A')"
    " || setweight(to_tsvector('simple'::regconfig,"
    " hubmi_unaccent(coalesce(summary, ''))), 'B')"
)
CHALLENGE_SEARCH_SQL = (
    "setweight(to_tsvector('simple'::regconfig,"
    " hubmi_unaccent(coalesce(title, ''))), 'A')"
    " || setweight(to_tsvector('simple'::regconfig, hubmi_unaccent("
    "coalesce(summary, '') || ' ' || coalesce(description, ''))), 'B')"
)


def _uuid_pk() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True)


def _ts(name: str, *, nullable: bool = False) -> sa.Column:
    if nullable:
        return sa.Column(name, sa.DateTime(timezone=True), nullable=True)
    return sa.Column(
        name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def _text_array(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.ARRAY(sa.Text()),
        nullable=False,
        server_default=sa.text("'{}'"),
    )


def _embedding_index(table: str) -> None:
    op.create_index(
        f"ix_{table}_embedding",
        table,
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def upgrade() -> None:
    material_kind = postgresql.ENUM(
        "report", "publication", "guide", "video", name="material_kind"
    )
    knowledge_status = postgresql.ENUM("draft", "published", name="knowledge_status")
    summary_state = postgresql.ENUM(
        "pending", "done", "no_text", "failed", name="summary_state"
    )
    import_status = postgresql.ENUM(
        "running", "done", "failed", name="import_status", create_type=False
    )
    import_trigger = postgresql.ENUM(
        "script", "admin", name="import_trigger", create_type=False
    )

    op.create_table(
        "material",
        _uuid_pk(),
        sa.Column("kind", material_kind, nullable=False, index=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True, index=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        _text_array("topics"),
        sa.Column("file_url", sa.Text(), nullable=False, unique=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_section", sa.Text(), nullable=False, server_default=""),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column("source_hash", sa.Text(), nullable=True),
        sa.Column(
            "summary_state", summary_state, nullable=False, server_default="pending"
        ),
        sa.Column("summary_hash", sa.Text(), nullable=True),
        sa.Column(
            "status",
            knowledge_status,
            nullable=False,
            server_default="published",
            index=True,
        ),
        _ts("imported_at", nullable=True),
        _ts("edited_at", nullable=True),
        _text_array("edited_fields"),
        sa.Column("embedding", Vector(DIM), nullable=True),
        sa.Column("embedded_hash", sa.Text(), nullable=True),
        sa.Column(
            "search",
            postgresql.TSVECTOR(),
            sa.Computed(MATERIAL_SEARCH_SQL, persisted=True),
        ),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index(
        "ix_material_search", "material", ["search"], postgresql_using="gin"
    )
    op.create_index(
        "ix_material_topics", "material", ["topics"], postgresql_using="gin"
    )
    _embedding_index("material")

    op.create_table(
        "material_text",
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("material.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        _text_array("pages"),
        sa.Column("chars", sa.Integer(), nullable=False, server_default="0"),
        _ts("created_at"),
        _ts("updated_at"),
    )

    op.create_table(
        "challenge",
        _uuid_pk(),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("area", sa.Text(), nullable=False, index=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "figures",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "source_pages",
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("material.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_hash", sa.Text(), nullable=True),
        sa.Column(
            "status",
            knowledge_status,
            nullable=False,
            server_default="published",
            index=True,
        ),
        _ts("verified_at", nullable=True),
        sa.Column("verified_by", sa.Text(), nullable=True),
        _ts("imported_at", nullable=True),
        _ts("edited_at", nullable=True),
        _text_array("edited_fields"),
        sa.Column("embedding", Vector(DIM), nullable=True),
        sa.Column("embedded_hash", sa.Text(), nullable=True),
        sa.Column(
            "search",
            postgresql.TSVECTOR(),
            sa.Computed(CHALLENGE_SEARCH_SQL, persisted=True),
        ),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index(
        "ix_challenge_search", "challenge", ["search"], postgresql_using="gin"
    )
    _embedding_index("challenge")

    op.create_table(
        "powiat_figure",
        _uuid_pk(),
        sa.Column("powiat", sa.Text(), nullable=False, index=True),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False, server_default=""),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False, server_default=""),
        sa.Column("page", sa.Integer(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.UniqueConstraint("powiat", "key", "year", name="uq_powiat_figure"),
    )

    op.create_table(
        "knowledge_run",
        _uuid_pk(),
        sa.Column("status", import_status, nullable=False),
        sa.Column("trigger", import_trigger, nullable=False),
        sa.Column("step", sa.Text(), nullable=False, server_default=""),
        sa.Column("done", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "counters",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error", sa.Text(), nullable=True),
        _ts("started_at"),
        _ts("finished_at", nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
    )


def downgrade() -> None:
    op.drop_table("knowledge_run")
    op.drop_table("powiat_figure")
    op.drop_table("challenge")
    op.drop_table("material_text")
    op.drop_table("material")
    for name in ("summary_state", "knowledge_status", "material_kind"):
        op.execute(f"DROP TYPE IF EXISTS {name}")
