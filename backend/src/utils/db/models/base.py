import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, func, text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field as SQLField


def uuid_pk() -> uuid.UUID:
    return SQLField(
        default_factory=uuid.uuid4,
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True),
    )


def uuid_fk(target: str, *, nullable: bool = True) -> Column:
    return Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey(target, ondelete="SET NULL"),
        nullable=nullable,
    )


def bigint_col(*, nullable: bool = True) -> Column:
    return Column(BigInteger, nullable=nullable)


def nullable_ts_col() -> datetime | None:
    return SQLField(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


def created_at_col() -> datetime:
    return SQLField(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )


def updated_at_col() -> datetime:
    return SQLField(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )


def jsonb_column(*, nullable: bool = False, default: str = "[]") -> Column:
    return Column(
        postgresql.JSONB,
        nullable=nullable,
        server_default=None if nullable else text(f"'{default}'::jsonb"),
    )
