"""kreator: ideas, idea threads in message

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-03 15:40:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DIM = 768


def upgrade() -> None:
    idea_stage = postgresql.ENUM(
        "idea", "preparing", "testing", "running", name="idea_stage"
    )
    idea_status = postgresql.ENUM(
        "new", "in_review", "accepted", "rejected", name="idea_status"
    )
    op.create_table(
        "idea",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("number", sa.Integer(), sa.Identity(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("essence", sa.Text(), nullable=False),
        sa.Column("for_whom", sa.Text(), nullable=False),
        sa.Column("stage", idea_stage, nullable=False, index=True),
        sa.Column(
            "canvas",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("powiat", sa.Text(), nullable=True, index=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column(
            "contact_consent", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status", idea_status, nullable=False, server_default="new", index=True
        ),
        sa.Column("edit_token_hash", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(DIM), nullable=True),
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
    op.create_index("ix_idea_created_at", "idea", ["created_at"])
    op.create_index(
        "ix_idea_embedding",
        "idea",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.add_column(
        "message",
        sa.Column(
            "idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("idea.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_message_idea_sent", "message", ["idea_id", "sent_at"])
    op.create_check_constraint(
        "ck_message_one_owner", "message", "num_nonnulls(need_id, idea_id) = 1"
    )


def downgrade() -> None:
    op.drop_constraint("ck_message_one_owner", "message", type_="check")
    op.drop_index("ix_message_idea_sent", table_name="message")
    op.drop_column("message", "idea_id")
    op.drop_table("idea")
    op.execute("DROP TYPE IF EXISTS idea_status")
    op.execute("DROP TYPE IF EXISTS idea_stage")
