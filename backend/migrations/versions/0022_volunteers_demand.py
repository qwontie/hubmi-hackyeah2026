"""Volunteers: application statuses, reports, messages; demand per innovation

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-04 01:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_STATUSES = ("new", "accepted", "rejected", "reported", "closed")
OLD_STATUSES = ("new", "contacted", "closed")


def _rebuild_status(values: Sequence[str], mapping: str) -> None:
    op.execute("ALTER TYPE signup_status RENAME TO signup_status_old")
    postgresql.ENUM(*values, name="signup_status").create(op.get_bind())
    op.execute("ALTER TABLE test_signup ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE test_signup ALTER COLUMN status TYPE signup_status "
        f"USING ({mapping})::signup_status"
    )
    op.execute("ALTER TABLE test_signup ALTER COLUMN status SET DEFAULT 'new'")
    op.execute("DROP TYPE signup_status_old")


def _signup_fk(*, unique: bool = False) -> sa.Column:
    return sa.Column(
        "signup_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("test_signup.id", ondelete="CASCADE"),
        nullable=False,
        unique=unique,
    )


def upgrade() -> None:
    _rebuild_status(
        NEW_STATUSES,
        "CASE status::text WHEN 'contacted' THEN 'new' ELSE status::text END",
    )
    op.add_column("test_signup", sa.Column("decision_reason", sa.Text(), nullable=True))
    op.add_column(
        "test_signup",
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    recommendation = postgresql.ENUM(
        "yes", "after_changes", "no", name="volunteer_recommendation"
    )
    message_kind = postgresql.ENUM(
        "message", "accept", "reject", name="volunteer_message_kind"
    )
    delivery = postgresql.ENUM(name="message_delivery", create_type=False)
    op.create_table(
        "volunteer_report",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _signup_fk(unique=True),
        sa.Column("activity", sa.Text(), nullable=False),
        sa.Column("participants", sa.Integer(), nullable=False),
        sa.Column("worked", sa.Text(), nullable=False),
        sa.Column("not_worked", sa.Text(), nullable=False),
        sa.Column("recommend", recommendation, nullable=False),
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
    )
    op.create_table(
        "volunteer_message",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _signup_fk(),
        sa.Column("kind", message_kind, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "admin_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("delivery_status", delivery, nullable=False),
        sa.Column("delivery_error", sa.Text(), nullable=True),
        sa.Column("provider_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_volunteer_message_signup_created",
        "volunteer_message",
        ["signup_id", "created_at"],
    )
    op.create_table(
        "innovation_demand",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "innovation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("innovation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("powiat", sa.Text(), nullable=False),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_key", sa.Text(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "innovation_id", "client_key", "day", name="uq_innovation_demand_client_day"
        ),
    )
    op.create_index(
        "ix_innovation_demand_innovation_powiat",
        "innovation_demand",
        ["innovation_id", "powiat"],
    )
    op.create_index(
        "ix_innovation_demand_created_at", "innovation_demand", ["created_at"]
    )


def downgrade() -> None:
    op.drop_table("innovation_demand")
    op.drop_table("volunteer_message")
    op.drop_table("volunteer_report")
    op.execute("DROP TYPE volunteer_message_kind")
    op.execute("DROP TYPE volunteer_recommendation")
    op.drop_column("test_signup", "decided_at")
    op.drop_column("test_signup", "decision_reason")
    _rebuild_status(
        OLD_STATUSES,
        "CASE status::text WHEN 'new' THEN 'new' WHEN 'closed' THEN 'closed' "
        "WHEN 'rejected' THEN 'closed' ELSE 'contacted' END",
    )
