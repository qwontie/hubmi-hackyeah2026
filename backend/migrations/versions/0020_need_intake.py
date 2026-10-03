"""Need intake without AI: duplicate key, reply cache, persistent rate counter

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-04 01:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("need", sa.Column("dedupe_key", sa.Text(), nullable=True))
    op.add_column(
        "need",
        sa.Column(
            "reply_suggestions", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.create_index("ix_need_dedupe_key", "need", ["dedupe_key", "created_at"])
    op.create_table(
        "rate_counter",
        sa.Column("key_hash", sa.String(length=64), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
    )
    op.create_index("ix_rate_counter_window_start", "rate_counter", ["window_start"])


def downgrade() -> None:
    op.drop_index("ix_rate_counter_window_start", table_name="rate_counter")
    op.drop_table("rate_counter")
    op.drop_index("ix_need_dedupe_key", table_name="need")
    op.drop_column("need", "reply_suggestions")
    op.drop_column("need", "dedupe_key")
