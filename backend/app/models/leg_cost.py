"""LegCost model — per-leg cost logging with audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PaymentMethod(str, PyEnum):
    CASH = "cash"
    CREDIT = "credit"
    CREDIT_CARD = "credit_card"
    WIRE = "wire"


class LegCostCategory(str, PyEnum):
    FUEL = "fuel"
    HANDLING = "handling"
    LANDING = "landing"
    CUSTOMS = "customs"
    PARKING = "parking"
    MISC = "misc"


class LegCost(Base):
    """A single cost logged against a specific flight leg.

    Each record represents one expense item (fuel, handling, landing fee,
    customs, parking, or miscellaneous) incurred during a particular leg
    of a mission.  Designed for airside/ramp-level cost tracking where
    the pilot or ops manager logs actuals at or after each stop.
    """

    __tablename__ = "leg_costs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    flight_leg_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("flight_legs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[LegCostCategory] = mapped_column(
        Enum(
            LegCostCategory,
            name="leg_cost_category",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(
            PaymentMethod,
            name="leg_payment_method",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<LegCost {self.category.value} ${self.amount:.2f}>"
