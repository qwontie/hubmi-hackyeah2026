"""Per-session admin logout

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-03 22:45:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_session_admin_id", "admin_session", ["admin_id"])
    op.create_index("ix_admin_session_expires_at", "admin_session", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_session_expires_at", table_name="admin_session")
    op.drop_index("ix_admin_session_admin_id", table_name="admin_session")
    op.drop_table("admin_session")
