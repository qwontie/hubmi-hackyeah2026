import uuid
from datetime import datetime

from sqlalchemy import Column, String
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from .base import created_at_col, uuid_pk


class AdminUser(SQLModel, table=True):
    __tablename__ = "admin_user"

    id: uuid.UUID = uuid_pk()
    login: str = SQLField(
        sa_column=Column(String, unique=True, index=True, nullable=False)
    )
    password_hash: str
    created_at: datetime | None = created_at_col()
