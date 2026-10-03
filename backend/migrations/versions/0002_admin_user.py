"""admin user

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03 12:35:50.880021

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel
import pgvector.sqlalchemy


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_user",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("login", sa.String(), nullable=False),
        sa.Column("password_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_user_login"), "admin_user", ["login"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_user_login"), table_name="admin_user")
    op.drop_table("admin_user")
