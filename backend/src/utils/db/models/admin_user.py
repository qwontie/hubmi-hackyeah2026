import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Column, Integer, String, Text, text
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from .base import created_at_col, uuid_pk


class AdminRole(StrEnum):
    ADMIN = "admin"
    EXPERT = "expert"


class AdminUser(SQLModel, table=True):
    __tablename__ = "admin_user"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'expert')", name="ck_admin_user_role"),
    )

    id: uuid.UUID = uuid_pk()
    login: str = SQLField(
        sa_column=Column(String, unique=True, index=True, nullable=False)
    )
    password_hash: str
    role: AdminRole = SQLField(
        default=AdminRole.ADMIN,
        sa_column=Column(Text, nullable=False, server_default=text("'admin'")),
    )
    display_name: str | None = SQLField(
        default=None, sa_column=Column(Text, nullable=True)
    )
    expertise: str | None = SQLField(
        default=None, sa_column=Column(Text, nullable=True)
    )
    email: str | None = SQLField(default=None, sa_column=Column(Text, nullable=True))
    token_version: int = SQLField(
        default=0, sa_column=Column(Integer, nullable=False, server_default=text("0"))
    )
    created_at: datetime | None = created_at_col()
