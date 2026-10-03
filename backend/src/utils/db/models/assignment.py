import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Text, text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, updated_at_col, uuid_pk


class AssignmentStatus(StrEnum):
    OPEN = "open"
    ANSWERED = "answered"


def owner_fk(target: str) -> Column:
    return Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey(target, ondelete="CASCADE"),
        nullable=True,
    )


class Assignment(SQLModel, table=True):
    __tablename__ = "assignment"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(need_id, idea_id) = 1", name="ck_assignment_one_item"
        ),
        CheckConstraint("status IN ('open', 'answered')", name="ck_assignment_status"),
        Index(
            "ux_assignment_expert_need",
            "expert_id",
            "need_id",
            unique=True,
            postgresql_where=text("need_id IS NOT NULL"),
        ),
        Index(
            "ux_assignment_expert_idea",
            "expert_id",
            "idea_id",
            unique=True,
            postgresql_where=text("idea_id IS NOT NULL"),
        ),
    )

    id: uuid.UUID = uuid_pk()
    expert_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("admin_user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    need_id: uuid.UUID | None = Field(default=None, sa_column=owner_fk("need.id"))
    idea_id: uuid.UUID | None = Field(default=None, sa_column=owner_fk("idea.id"))
    note: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: AssignmentStatus = Field(
        default=AssignmentStatus.OPEN,
        sa_column=Column(Text, nullable=False, server_default=text("'open'")),
    )
    assigned_by: str = Field(sa_column=Column(Text, nullable=False))
    answered_at: datetime | None = nullable_ts_col()
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


class ExpertNote(SQLModel, table=True):
    __tablename__ = "expert_note"

    id: uuid.UUID = uuid_pk()
    assignment_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("assignment.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    body: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = created_at_col()


__all__ = ["Assignment", "AssignmentStatus", "ExpertNote"]
