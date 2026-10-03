"""library, needs and clusters

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-03 16:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DIM = 768

SEARCH_SQL = (
    "setweight(to_tsvector('simple'::regconfig, hubmi_unaccent(coalesce(title, ''))), 'A') || "
    "setweight(to_tsvector('simple'::regconfig, hubmi_unaccent(coalesce(lead, ''))), 'B') || "
    "setweight(to_tsvector('simple'::regconfig, hubmi_unaccent("
    "coalesce(problems, '') || ' ' || coalesce(target_group, ''))), 'B') || "
    "setweight(to_tsvector('simple'::regconfig, hubmi_unaccent("
    "coalesce(what_it_is, '') || ' ' || coalesce(who_can_use, '') || ' ' || "
    "coalesce(effectiveness, ''))), 'C')"
)


def _uuid_pk() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def _count(name: str) -> sa.Column:
    return sa.Column(name, sa.Integer(), nullable=False, server_default="0")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        "CREATE OR REPLACE FUNCTION hubmi_unaccent(text) RETURNS text "
        "LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT "
        "AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$"
    )

    innovation_status = postgresql.ENUM("draft", "published", name="innovation_status")
    need_origin = postgresql.ENUM("match", "form", name="need_origin")
    need_status = postgresql.ENUM("new", "answered", "closed", name="need_status")
    import_status = postgresql.ENUM("running", "done", "failed", name="import_status")
    import_trigger = postgresql.ENUM("script", "admin", name="import_trigger")

    op.create_table(
        "category",
        _uuid_pk(),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("icon_url", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )

    op.create_table(
        "innovation",
        _uuid_pk(),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "category_slug",
            sa.Text(),
            sa.ForeignKey("category.slug", onupdate="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("lead", sa.Text(), nullable=False, server_default=""),
        sa.Column("what_it_is", sa.Text(), nullable=False, server_default=""),
        sa.Column("problems", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_group", sa.Text(), nullable=False, server_default=""),
        sa.Column("who_can_use", sa.Text(), nullable=False, server_default=""),
        sa.Column("effectiveness", sa.Text(), nullable=True),
        sa.Column(
            "authors",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("qr_url", sa.Text(), nullable=True),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("materials_url", sa.Text(), nullable=True),
        sa.Column("brochure_url", sa.Text(), nullable=True),
        sa.Column("license", sa.Text(), nullable=True),
        sa.Column(
            "status",
            innovation_status,
            nullable=False,
            server_default="published",
            index=True,
        ),
        sa.Column("source_url", sa.Text(), nullable=True, unique=True),
        sa.Column("source_hash", sa.Text(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "edited_fields",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("embedding", Vector(DIM), nullable=True),
        sa.Column("embedded_hash", sa.Text(), nullable=True),
        sa.Column(
            "search", postgresql.TSVECTOR(), sa.Computed(SEARCH_SQL, persisted=True)
        ),
        *_timestamps(),
    )
    op.create_index(
        "ix_innovation_search", "innovation", ["search"], postgresql_using="gin"
    )
    op.create_index(
        "ix_innovation_embedding",
        "innovation",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "need_cluster",
        _uuid_pk(),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "category_slug",
            sa.Text(),
            sa.ForeignKey("category.slug", onupdate="CASCADE", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("centroid", Vector(DIM), nullable=True),
        sa.Column("last_need_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "summary_stale", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        *_timestamps(),
    )
    op.create_index(
        "ix_need_cluster_centroid",
        "need_cluster",
        ["centroid"],
        postgresql_using="hnsw",
        postgresql_ops={"centroid": "vector_cosine_ops"},
    )

    op.create_table(
        "need",
        _uuid_pk(),
        sa.Column("number", sa.Integer(), sa.Identity(), nullable=False, unique=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("origin", need_origin, nullable=False),
        sa.Column("powiat", sa.Text(), nullable=True, index=True),
        sa.Column(
            "category_slug",
            sa.Text(),
            sa.ForeignKey("category.slug", onupdate="CASCADE", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column(
            "contact_consent", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "nothing_fits", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "status", need_status, nullable=False, server_default="new", index=True
        ),
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("need_cluster.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("edit_token_hash", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(DIM), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_need_created_at", "need", ["created_at"])
    op.create_index(
        "ix_need_embedding",
        "need",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "match_result",
        _uuid_pk(),
        sa.Column(
            "need_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("need.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "innovation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("innovation.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "import_run",
        _uuid_pk(),
        sa.Column("status", import_status, nullable=False),
        sa.Column("trigger", import_trigger, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        _count("total"),
        _count("created"),
        _count("updated"),
        _count("unchanged"),
        _count("skipped_edited"),
        _count("failed"),
        sa.Column("error", sa.Text(), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "ai_call",
        _uuid_pk(),
        sa.Column("kind", sa.Text(), nullable=False, index=True),
        sa.Column("model", sa.Text(), nullable=False),
        _count("input_tokens"),
        _count("output_tokens"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        _count("latency_ms"),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_ai_call_created_at", "ai_call", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_call")
    op.drop_table("import_run")
    op.drop_table("match_result")
    op.drop_table("need")
    op.drop_table("need_cluster")
    op.drop_table("innovation")
    op.drop_table("category")
    for name in (
        "import_trigger",
        "import_status",
        "need_status",
        "need_origin",
        "innovation_status",
    ):
        op.execute(f"DROP TYPE IF EXISTS {name}")
    op.execute("DROP FUNCTION IF EXISTS hubmi_unaccent(text)")
