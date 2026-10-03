import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, updated_at_col, uuid_pk


class MessageDirection(StrEnum):
    TO_AUTHOR = "to_author"
    FROM_AUTHOR = "from_author"


class MessageDelivery(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"


def _enum[T: StrEnum](enum: type[T], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda e: [m.value for m in e])


class Message(SQLModel, table=True):
    __tablename__ = "message"
    __table_args__ = (Index("ix_message_need_sent", "need_id", "sent_at"),)

    id: uuid.UUID = uuid_pk()
    need_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("need.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    direction: MessageDirection = Field(
        sa_column=Column(_enum(MessageDirection, "message_direction"), nullable=False)
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
    delivery_status: MessageDelivery | None = Field(
        default=None,
        sa_column=Column(_enum(MessageDelivery, "message_delivery"), nullable=True),
    )
    delivery_error: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    provider_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    read_at: datetime | None = nullable_ts_col()
    sent_at: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = ["Message", "MessageDelivery", "MessageDirection"]
