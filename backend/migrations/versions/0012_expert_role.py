"""gaps-api: expert role, assignments, expert notes, expert messages

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-03 18:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "admin_user",
        sa.Column("role", sa.Text(), nullable=False, server_default=sa.text("'admin'")),
    )
    op.add_column("admin_user", sa.Column("display_name", sa.Text(), nullable=True))
    op.add_column("admin_user", sa.Column("expertise", sa.Text(), nullable=True))
    op.add_column("admin_user", sa.Column("email", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_admin_user_role", "admin_user", "role IN ('admin', 'expert')"
    )
    op.add_column("message", sa.Column("expert_name", sa.Text(), nullable=True))
    op.add_column("message", sa.Column("expert_field", sa.Text(), nullable=True))
    op.create_table(
        "assignment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "expert_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "need_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("need.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("idea.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'open'")
        ),
        sa.Column("assigned_by", sa.Text(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "num_nonnulls(need_id, idea_id) = 1", name="ck_assignment_one_item"
        ),
        sa.CheckConstraint(
            "status IN ('open', 'answered')", name="ck_assignment_status"
        ),
    )
    op.create_index("ix_assignment_expert_id", "assignment", ["expert_id"])
    op.create_index(
        "ux_assignment_expert_need",
        "assignment",
        ["expert_id", "need_id"],
        unique=True,
        postgresql_where=sa.text("need_id IS NOT NULL"),
    )
    op.create_index(
        "ux_assignment_expert_idea",
        "assignment",
        ["expert_id", "idea_id"],
        unique=True,
        postgresql_where=sa.text("idea_id IS NOT NULL"),
    )
    op.create_table(
        "expert_note",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assignment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assignment.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_expert_note_assignment_id", "expert_note", ["assignment_id"])


def downgrade() -> None:
    op.drop_table("expert_note")
    op.drop_table("assignment")
    op.drop_column("message", "expert_field")
    op.drop_column("message", "expert_name")
    op.drop_constraint("ck_admin_user_role", "admin_user", type_="check")
    op.drop_column("admin_user", "email")
    op.drop_column("admin_user", "expertise")
    op.drop_column("admin_user", "display_name")
    op.drop_column("admin_user", "role")
