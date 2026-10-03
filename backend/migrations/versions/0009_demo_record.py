"""demo record registry for the demo data script

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-03 17:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "demo_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("kind", "key", name="uq_demo_record_kind_key"),
    )
    op.create_index("ix_demo_record_kind", "demo_record", ["kind"])
    op.create_index("ix_demo_record_row_id", "demo_record", ["row_id"])


def downgrade() -> None:
    op.drop_index("ix_demo_record_row_id", table_name="demo_record")
    op.drop_index("ix_demo_record_kind", table_name="demo_record")
    op.drop_table("demo_record")
