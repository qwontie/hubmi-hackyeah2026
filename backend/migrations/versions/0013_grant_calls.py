"""gaps-api: grant calls, applications drafted from ideas, call subscribers

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-03 19:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "grant_call",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'draft'")
        ),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column(
            "sections",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("template", sa.Text(), nullable=True),
        sa.Column(
            "demo", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("notified_open_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("closes_at > opens_at", name="ck_grant_call_dates"),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'cancelled')", name="ck_grant_call_status"
        ),
    )
    op.create_index("ix_grant_call_opens_at", "grant_call", ["opens_at"])
    op.create_index("ix_grant_call_closes_at", "grant_call", ["closes_at"])
    op.create_table(
        "grant_application",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("number", sa.Integer(), sa.Identity(), nullable=False, unique=True),
        sa.Column(
            "call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("grant_call.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("idea.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sections",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'draft'")
        ),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.UniqueConstraint("call_id", "idea_id", name="ux_grant_application_idea"),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'in_review', 'accepted', 'rejected')",
            name="ck_grant_application_status",
        ),
    )
    op.create_index("ix_grant_application_call_id", "grant_application", ["call_id"])
    op.create_index("ix_grant_application_idea_id", "grant_application", ["idea_id"])
    op.create_table(
        "grant_subscriber",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
    )


def downgrade() -> None:
    op.drop_table("grant_subscriber")
    op.drop_table("grant_application")
    op.drop_table("grant_call")
