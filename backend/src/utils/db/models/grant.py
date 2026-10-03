import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import false as sa_false
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, updated_at_col, uuid_pk


class GrantCallStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class GrantCall(SQLModel, table=True):
    __tablename__ = "grant_call"
    __table_args__ = (
        CheckConstraint("closes_at > opens_at", name="ck_grant_call_dates"),
        CheckConstraint(
            "status IN ('draft', 'published', 'cancelled')", name="ck_grant_call_status"
        ),
    )

    id: uuid.UUID = uuid_pk()
    title: str = Field(sa_column=Column(Text, nullable=False))
    description: str = Field(sa_column=Column(Text, nullable=False))
    opens_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    closes_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    status: GrantCallStatus = Field(
        default=GrantCallStatus.DRAFT,
        sa_column=Column(Text, nullable=False, server_default=text("'draft'")),
    )
    source_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    sections: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(
            postgresql.JSONB, nullable=False, server_default=text("'[]'::jsonb")
        ),
    )
    template: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    demo: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=sa_false()),
    )
    notified_open_at: datetime | None = nullable_ts_col()
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


class GrantApplication(SQLModel, table=True):
    __tablename__ = "grant_application"
    __table_args__ = (
        UniqueConstraint("call_id", "idea_id", name="ux_grant_application_idea"),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'in_review', 'accepted', 'rejected')",
            name="ck_grant_application_status",
        ),
    )

    id: uuid.UUID = uuid_pk()
    number: int | None = Field(
        default=None, sa_column=Column(Integer, Identity(), nullable=False, unique=True)
    )
    call_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("grant_call.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    idea_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("idea.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    sections: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            postgresql.JSONB, nullable=False, server_default=text("'{}'::jsonb")
        ),
    )
    status: ApplicationStatus = Field(
        default=ApplicationStatus.DRAFT,
        sa_column=Column(Text, nullable=False, server_default=text("'draft'")),
    )
    model: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    submitted_at: datetime | None = nullable_ts_col()
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


class GrantSubscriber(SQLModel, table=True):
    __tablename__ = "grant_subscriber"

    id: uuid.UUID = uuid_pk()
    email: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    consent_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    confirmed_at: datetime | None = nullable_ts_col()
    unsubscribed_at: datetime | None = nullable_ts_col()
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = [
    "ApplicationStatus",
    "GrantApplication",
    "GrantCall",
    "GrantCallStatus",
    "GrantSubscriber",
]
