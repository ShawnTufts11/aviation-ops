"""FinancialRecord model — auto-created from flights and maintenance."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RecordType(str, PyEnum):
    REVENUE = "revenue"
    COST = "cost"
    INVOICE = "invoice"
    EXPENSE = "expense"


class CostCategory(str, PyEnum):
    CHARTER_REVENUE = "charter_revenue"
    CARGO_REVENUE = "cargo_revenue"
    FUEL = "fuel"
    MAINTENANCE = "maintenance"
    CREW = "crew"
    INSURANCE = "insurance"
    LANDING_FEES = "landing_fees"
    HANDLING = "handling"
    HANGAR = "hangar"
    TRAINING = "training"
    CUSTOMS = "customs"
    MISC = "misc"


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    aircraft_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("aircraft.id", ondelete="SET NULL"), nullable=True, index=True
    )
    flight_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("flights.id", ondelete="SET NULL"), nullable=True, index=True
    )
    maintenance_task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("maintenance_tasks.id", ondelete="SET NULL"), nullable=True
    )

    record_type: Mapped[RecordType] = mapped_column(
        Enum(RecordType, name="fin_record_type", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    category: Mapped[CostCategory] = mapped_column(
        Enum(CostCategory, name="fin_cost_category", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<FinancialRecord {self.record_type.value} ${self.amount} ({self.category.value})>"
