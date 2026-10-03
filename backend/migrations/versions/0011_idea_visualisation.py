"""gaps-api: idea visualisation image and counters

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-03 18:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "idea",
        sa.Column(
            "visualisation_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "idea", sa.Column("visualisation_version", sa.Integer(), nullable=True)
    )
    op.add_column("idea", sa.Column("visualisation_alt", sa.Text(), nullable=True))
    op.create_table(
        "idea_visualisation",
        sa.Column(
            "idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("idea.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("image", sa.LargeBinary(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("alt", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("idea_visualisation")
    op.drop_column("idea", "visualisation_alt")
    op.drop_column("idea", "visualisation_version")
    op.drop_column("idea", "visualisation_count")
