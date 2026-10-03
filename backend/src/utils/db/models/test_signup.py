import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, updated_at_col, uuid_pk


class TesterRole(StrEnum):
    RESIDENT = "resident"
    NGO = "ngo"
    LOCAL_GOVERNMENT = "local_government"
    EXPERT = "expert"


class SignupStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    CLOSED = "closed"


def _enum[T: StrEnum](enum: type[T], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda e: [m.value for m in e])


class TestSignup(SQLModel, table=True):
    __tablename__ = "test_signup"
    __table_args__ = (Index("ix_test_signup_created_at", "created_at"),)

    id: uuid.UUID = uuid_pk()
    innovation_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("innovation.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    who: TesterRole = Field(
        sa_column=Column(_enum(TesterRole, "tester_role"), nullable=False, index=True)
    )
    organization: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    powiat: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True, index=True)
    )
    contact_email: str = Field(sa_column=Column(Text, nullable=False))
    consent_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    note: str = Field(default="", sa_column=Column(Text, nullable=False))
    status: SignupStatus = Field(
        default=SignupStatus.NEW,
        sa_column=Column(
            _enum(SignupStatus, "signup_status"),
            nullable=False,
            server_default=SignupStatus.NEW.value,
            index=True,
        ),
    )
    created_at: datetime = created_at_col()
    updated_at: datetime = updated_at_col()


__all__ = ["SignupStatus", "TestSignup", "TesterRole"]
