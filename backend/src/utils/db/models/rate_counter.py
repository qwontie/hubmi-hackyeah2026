from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlmodel import Field, SQLModel


class RateCounter(SQLModel, table=True):
    __tablename__ = "rate_counter"

    key_hash: str = Field(sa_column=Column(String(64), primary_key=True))
    window_start: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    hits: int = Field(sa_column=Column(Integer, nullable=False))
