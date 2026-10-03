"""public-api: voter key on feedback votes, problem link on ideas

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-03 16:50:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("feedback", sa.Column("voter_hash", sa.Text(), nullable=True))
    op.create_index(
        "ux_feedback_voter_vote",
        "feedback",
        ["voter_hash", "innovation_id"],
        unique=True,
        postgresql_where=sa.text("voter_hash IS NOT NULL AND kind <> 'improvement'"),
    )
    op.add_column(
        "idea",
        sa.Column(
            "problem_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("need_cluster.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_idea_problem_id", "idea", ["problem_id"])


def downgrade() -> None:
    op.drop_index("ix_idea_problem_id", table_name="idea")
    op.drop_column("idea", "problem_id")
    op.drop_index("ux_feedback_voter_vote", table_name="feedback")
    op.drop_column("feedback", "voter_hash")
