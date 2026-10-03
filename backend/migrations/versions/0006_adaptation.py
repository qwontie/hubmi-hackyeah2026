"""middleman: adaptation plans

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-03 15:20:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "adaptation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "innovation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("innovation.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("institution_type", sa.Text(), nullable=False, index=True),
        sa.Column("place", sa.Text(), nullable=False),
        sa.Column("powiat", sa.Text(), nullable=True, index=True),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("plan", postgresql.JSONB(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_adaptation_created_at", "adaptation", ["created_at"])


def downgrade() -> None:
    op.drop_table("adaptation")
