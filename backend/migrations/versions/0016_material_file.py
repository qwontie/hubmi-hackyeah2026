"""backend-content: files of added materials, pdf validators, scheduled imports

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-03 22:10:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE import_trigger ADD VALUE IF NOT EXISTS 'schedule'")
    op.add_column("material", sa.Column("source_etag", sa.Text(), nullable=True))
    op.add_column("material", sa.Column("source_modified", sa.Text(), nullable=True))
    op.create_table(
        "material_file",
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("material.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("material_file")
    op.drop_column("material", "source_modified")
    op.drop_column("material", "source_etag")
