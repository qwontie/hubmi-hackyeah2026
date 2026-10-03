"""dialogue messages and admin audit log

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-03 15:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp(name: str) -> sa.Column:
    return sa.Column(
        name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def upgrade() -> None:
    direction = postgresql.ENUM("to_author", "from_author", name="message_direction")
    delivery = postgresql.ENUM(
        "pending", "sent", "skipped", "failed", name="message_delivery"
    )

    op.create_table(
        "message",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "need_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("need.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("direction", direction, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "admin_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("delivery_status", delivery, nullable=True),
        sa.Column("delivery_error", sa.Text(), nullable=True),
        sa.Column("provider_id", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        _timestamp("sent_at"),
        _timestamp("created_at"),
        _timestamp("updated_at"),
    )
    op.create_index("ix_message_need_sent", "message", ["need_id", "sent_at"])

    op.create_table(
        "admin_action",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "admin_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("admin_login", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        _timestamp("created_at"),
    )
    op.create_index("ix_admin_action_admin_id", "admin_action", ["admin_id"])
    op.create_index("ix_admin_action_created_at", "admin_action", ["created_at"])
    op.create_index(
        "ix_admin_action_target", "admin_action", ["target_type", "target_id"]
    )


def downgrade() -> None:
    op.drop_table("admin_action")
    op.drop_table("message")
    op.execute("DROP TYPE IF EXISTS message_delivery")
    op.execute("DROP TYPE IF EXISTS message_direction")
