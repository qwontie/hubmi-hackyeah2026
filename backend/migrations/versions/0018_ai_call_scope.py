"""Separate public and batch AI budgets

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-03 21:55:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BATCH_KINDS = (
    "adaptation",
    "challenge_extract",
    "challenge_figures",
    "embed_challenge",
    "embed_innovation",
    "innovation",
    "innovation_image",
    "innovation_image_judge",
    "innovation_image_prompt",
)


def upgrade() -> None:
    op.add_column(
        "ai_call",
        sa.Column(
            "scope", sa.Text(), server_default=sa.text("'public'"), nullable=False
        ),
    )
    op.create_check_constraint(
        "ck_ai_call_scope", "ai_call", "scope IN ('public', 'batch')"
    )
    op.create_index("ix_ai_call_scope", "ai_call", ["scope"])
    op.execute(
        sa.update(sa.table("ai_call", sa.column("kind"), sa.column("scope")))
        .where(sa.column("kind").in_(BATCH_KINDS))
        .values(scope="batch")
    )


def downgrade() -> None:
    op.drop_index("ix_ai_call_scope", table_name="ai_call")
    op.drop_constraint("ck_ai_call_scope", "ai_call", type_="check")
    op.drop_column("ai_call", "scope")
