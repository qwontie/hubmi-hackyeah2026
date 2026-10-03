"""backend-content: stored images for innovations

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-03 20:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCES = ("rops", "youtube", "generated")


def upgrade() -> None:
    op.add_column("innovation", sa.Column("image_version", sa.Integer(), nullable=True))
    op.add_column("innovation", sa.Column("image_source", sa.Text(), nullable=True))
    op.add_column("innovation", sa.Column("image_alt", sa.Text(), nullable=True))
    op.create_table(
        "innovation_image",
        sa.Column(
            "innovation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("innovation.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source", sa.Enum(*SOURCES, name="image_source"), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("image", sa.LargeBinary(), nullable=False),
        sa.Column("card", sa.LargeBinary(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("alt", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("innovation_image")
    sa.Enum(name="image_source").drop(op.get_bind(), checkfirst=True)
    op.drop_column("innovation", "image_alt")
    op.drop_column("innovation", "image_source")
    op.drop_column("innovation", "image_version")
