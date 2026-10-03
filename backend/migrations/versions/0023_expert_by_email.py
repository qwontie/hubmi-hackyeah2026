"""Experts without accounts: assignments addressed to an e-mail

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-04 01:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("assignment", "expert_id", nullable=True)
    for name in ("expert_email", "expert_name", "expert_field", "delivery_status"):
        op.add_column("assignment", sa.Column(name, sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_assignment_one_expert",
        "assignment",
        "num_nonnulls(expert_id, expert_email) = 1",
    )
    for item in ("need_id", "idea_id"):
        op.create_index(
            f"ux_assignment_email_{item.removesuffix('_id')}",
            "assignment",
            [sa.text("lower(expert_email)"), item],
            unique=True,
            postgresql_where=sa.text(
                f"{item} IS NOT NULL AND expert_email IS NOT NULL"
            ),
        )


def downgrade() -> None:
    op.execute("DELETE FROM assignment WHERE expert_id IS NULL")
    for item in ("need", "idea"):
        op.drop_index(f"ux_assignment_email_{item}", table_name="assignment")
    op.drop_constraint("ck_assignment_one_expert", "assignment", type_="check")
    for name in ("delivery_status", "expert_field", "expert_name", "expert_email"):
        op.drop_column("assignment", name)
    op.alter_column("assignment", "expert_id", nullable=False)
