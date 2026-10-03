"""backend-core: revocable sessions and login throttling

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-03 21:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "admin_user",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "auth_login_guard",
        sa.Column("key_hash", sa.String(length=64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_auth_login_guard_updated_at", "auth_login_guard", ["updated_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_auth_login_guard_updated_at", table_name="auth_login_guard")
    op.drop_table("auth_login_guard")
    op.drop_column("admin_user", "token_version")
