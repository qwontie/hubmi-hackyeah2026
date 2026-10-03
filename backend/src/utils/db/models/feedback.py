import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, Enum, ForeignKey, Index, Text, text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, updated_at_col, uuid_pk


class FeedbackKind(StrEnum):
    FITS = "fits"
    DOES_NOT_FIT = "does_not_fit"
    IMPROVEMENT = "improvement"


VOTE_KINDS = (FeedbackKind.FITS, FeedbackKind.DOES_NOT_FIT)


class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"
    __table_args__ = (
        Index(
            "ux_feedback_need_vote",
            "need_id",
            "innovation_id",
            unique=True,
            postgresql_where=text("need_id IS NOT NULL AND kind <> 'improvement'"),
        ),
        Index("ix_feedback_created_at", "created_at"),
    )

    id: uuid.UUID = uuid_pk()
    innovation_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("innovation.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    kind: FeedbackKind = Field(
        sa_column=Column(
            Enum(
                FeedbackKind,
                name="feedback_kind",
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
            index=True,
        )
    )
    need_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("need.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    comment: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = ["VOTE_KINDS", "Feedback", "FeedbackKind"]
