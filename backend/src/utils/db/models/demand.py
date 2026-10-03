import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel

from .base import created_at_col, nullable_ts_col, uuid_pk


class InnovationDemand(SQLModel, table=True):
    __tablename__ = "innovation_demand"
    __table_args__ = (
        UniqueConstraint(
            "innovation_id", "client_key", "day", name="uq_innovation_demand_client_day"
        ),
        Index("ix_innovation_demand_innovation_powiat", "innovation_id", "powiat"),
        Index("ix_innovation_demand_created_at", "created_at"),
    )

    id: uuid.UUID = uuid_pk()
    innovation_id: uuid.UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("innovation.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    powiat: str = Field(sa_column=Column(Text, nullable=False))
    contact_email: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    consent_at: datetime | None = nullable_ts_col()
    client_key: str = Field(sa_column=Column(Text, nullable=False))
    day: date = Field(sa_column=Column(Date, nullable=False))
    created_at: datetime = created_at_col()


__all__ = ["InnovationDemand"]
