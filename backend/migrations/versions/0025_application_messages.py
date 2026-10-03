"""Staff replies to grant applications without an idea

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-04 01:45:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "message",
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("grant_application.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_message_application_sent", "message", ["application_id", "sent_at"]
    )
    op.drop_constraint("ck_message_one_owner", "message", type_="check")
    op.create_check_constraint(
        "ck_message_one_owner",
        "message",
        "num_nonnulls(need_id, idea_id, application_id) = 1",
    )


def downgrade() -> None:
    op.execute("DELETE FROM message WHERE application_id IS NOT NULL")
    op.drop_constraint("ck_message_one_owner", "message", type_="check")
    op.create_check_constraint(
        "ck_message_one_owner", "message", "num_nonnulls(need_id, idea_id) = 1"
    )
    op.drop_index("ix_message_application_sent", table_name="message")
    op.drop_column("message", "application_id")
