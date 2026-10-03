import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, Enum, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, updated_at_col, uuid_pk
from .message import MessageDelivery


class Recommendation(StrEnum):
    YES = "yes"
    AFTER_CHANGES = "after_changes"
    NO = "no"


class VolunteerMessageKind(StrEnum):
    MESSAGE = "message"
    ACCEPT = "accept"
    REJECT = "reject"


def _enum[T: StrEnum](enum: type[T], name: str, *, create: bool = True) -> Enum:
    return Enum(
        enum,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        create_type=create,
    )


def _signup_fk(*, unique: bool = False) -> Column:
    return Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("test_signup.id", ondelete="CASCADE"),
        nullable=False,
        unique=unique,
        index=not unique,
    )


class VolunteerReport(SQLModel, table=True):
    __tablename__ = "volunteer_report"

    id: uuid.UUID = uuid_pk()
    signup_id: uuid.UUID = Field(sa_column=_signup_fk(unique=True))
    activity: str = Field(sa_column=Column(Text, nullable=False))
    participants: int = Field(sa_column=Column(Integer, nullable=False))
    worked: str = Field(sa_column=Column(Text, nullable=False))
    not_worked: str = Field(sa_column=Column(Text, nullable=False))
    recommend: Recommendation = Field(
        sa_column=Column(
            _enum(Recommendation, "volunteer_recommendation"), nullable=False
        )
    )
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


class VolunteerMessage(SQLModel, table=True):
    __tablename__ = "volunteer_message"
    __table_args__ = (
        Index("ix_volunteer_message_signup_created", "signup_id", "created_at"),
    )

    id: uuid.UUID = uuid_pk()
    signup_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("test_signup.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    kind: VolunteerMessageKind = Field(
        sa_column=Column(
            _enum(VolunteerMessageKind, "volunteer_message_kind"), nullable=False
        )
    )
    body: str = Field(sa_column=Column(Text, nullable=False))
    admin_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("admin_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    delivery_status: MessageDelivery = Field(
        default=MessageDelivery.PENDING,
        sa_column=Column(
            _enum(MessageDelivery, "message_delivery", create=False), nullable=False
        ),
    )
    delivery_error: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    provider_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = created_at_col()


__all__ = [
    "Recommendation",
    "VolunteerMessage",
    "VolunteerMessageKind",
    "VolunteerReport",
]
