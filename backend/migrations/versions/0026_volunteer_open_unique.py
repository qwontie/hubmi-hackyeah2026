"""One open volunteer application per e-mail per innovation

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-04 01:50:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OPEN = "status IN ('new', 'accepted', 'reported')"


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE test_signup SET status = 'closed'
        WHERE id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY innovation_id, lower(contact_email)
                    ORDER BY created_at DESC
                ) AS n
                FROM test_signup WHERE {OPEN}
            ) ranked WHERE n > 1
        )
        """
    )
    op.create_index(
        "ux_test_signup_open_email",
        "test_signup",
        ["innovation_id", sa.text("lower(contact_email)")],
        unique=True,
        postgresql_where=sa.text(OPEN),
    )


def downgrade() -> None:
    op.drop_index("ux_test_signup_open_email", table_name="test_signup")
