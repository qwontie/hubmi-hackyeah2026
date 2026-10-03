"""Junk needs, staff-named groups, title embeddings, anonymous search log

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-04 01:10:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE need_status ADD VALUE IF NOT EXISTS 'junk'")
    op.add_column(
        "need_cluster",
        sa.Column(
            "title_locked", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    op.add_column(
        "need_cluster", sa.Column("title_embedding", Vector(768), nullable=True)
    )
    op.create_table(
        "search_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("category_slug", sa.Text(), nullable=True),
        sa.Column(
            "slugs", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "scores", postgresql.ARRAY(sa.Float()), server_default="{}", nullable=False
        ),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN ('ok', 'unclear', 'no_match')", name="ck_search_log_outcome"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_log_created_at", "search_log", ["created_at"])


def downgrade() -> None:
    op.execute("UPDATE need SET status = 'closed' WHERE status = 'junk'")
    op.drop_index("ix_search_log_created_at", table_name="search_log")
    op.drop_table("search_log")
    op.drop_column("need_cluster", "title_embedding")
    op.drop_column("need_cluster", "title_locked")
