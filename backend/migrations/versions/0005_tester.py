"""tester: feedback and test signups

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-03 16:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
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


def _innovation_fk() -> sa.Column:
    return sa.Column(
        "innovation_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("innovation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def upgrade() -> None:
    feedback_kind = postgresql.ENUM(
        "fits", "does_not_fit", "improvement", name="feedback_kind"
    )
    tester_role = postgresql.ENUM(
        "resident", "ngo", "local_government", "expert", name="tester_role"
    )
    signup_status = postgresql.ENUM("new", "contacted", "closed", name="signup_status")

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _innovation_fk(),
        sa.Column("kind", feedback_kind, nullable=False, index=True),
        sa.Column(
            "need_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("need.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"])
    op.create_index(
        "ux_feedback_need_vote",
        "feedback",
        ["need_id", "innovation_id"],
        unique=True,
        postgresql_where=sa.text("need_id IS NOT NULL AND kind <> 'improvement'"),
    )

    op.create_table(
        "test_signup",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _innovation_fk(),
        sa.Column("who", tester_role, nullable=False, index=True),
        sa.Column("organization", sa.Text(), nullable=True),
        sa.Column("powiat", sa.Text(), nullable=True, index=True),
        sa.Column("contact_email", sa.Text(), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "status", signup_status, nullable=False, server_default="new", index=True
        ),
        *_timestamps(),
    )
    op.create_index("ix_test_signup_created_at", "test_signup", ["created_at"])


def downgrade() -> None:
    op.drop_table("test_signup")
    op.drop_table("feedback")
    op.execute("DROP TYPE IF EXISTS signup_status")
    op.execute("DROP TYPE IF EXISTS tester_role")
    op.execute("DROP TYPE IF EXISTS feedback_kind")
