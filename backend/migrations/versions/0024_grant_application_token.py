"""Grant applications without an idea: own token and contact

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-04 02:40:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("grant_application", "idea_id", nullable=True)
    op.add_column(
        "grant_application", sa.Column("edit_token_hash", sa.Text(), nullable=True)
    )
    op.add_column(
        "grant_application", sa.Column("contact_email", sa.Text(), nullable=True)
    )
    op.add_column(
        "grant_application",
        sa.Column(
            "contact_consent", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )


def downgrade() -> None:
    op.execute("DELETE FROM grant_application WHERE idea_id IS NULL")
    op.drop_column("grant_application", "contact_consent")
    op.drop_column("grant_application", "contact_email")
    op.drop_column("grant_application", "edit_token_hash")
    op.alter_column("grant_application", "idea_id", nullable=False)
