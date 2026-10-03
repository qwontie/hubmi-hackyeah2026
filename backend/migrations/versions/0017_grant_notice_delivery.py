"""Persist grant notice delivery per subscriber

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-03 21:05:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "grant_notice_delivery",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscriber_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notice_key", sa.Text(), nullable=False),
        sa.Column("opened", sa.Boolean(), nullable=False),
        sa.Column(
            "status", sa.Text(), server_default=sa.text("'pending'"), nullable=False
        ),
        sa.Column(
            "attempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'failed', 'skipped', 'sent')",
            name="ck_grant_notice_delivery_status",
        ),
        sa.ForeignKeyConstraint(["call_id"], ["grant_call.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subscriber_id"], ["grant_subscriber.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "call_id",
            "subscriber_id",
            "notice_key",
            name="uq_grant_notice_delivery_event",
        ),
    )
    op.create_index(
        "ix_grant_notice_delivery_call_id", "grant_notice_delivery", ["call_id"]
    )
    op.create_index(
        "ix_grant_notice_delivery_subscriber_id",
        "grant_notice_delivery",
        ["subscriber_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_grant_notice_delivery_subscriber_id", table_name="grant_notice_delivery"
    )
    op.drop_index(
        "ix_grant_notice_delivery_call_id", table_name="grant_notice_delivery"
    )
    op.drop_table("grant_notice_delivery")
