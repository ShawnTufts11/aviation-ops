"""Pydantic schemas for flight cost reconciliation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ActualCostLineItems(BaseModel):
    """Cost breakdown with per-item and total."""
    landing_fee_usd: float = 0.0
    overnight_parking_usd: float = 0.0
    handling_fee_usd: float = 0.0
    customs_fee_usd: float = 0.0
    total: float = 0.0


class ActualCostsCreate(BaseModel):
    """Actual costs paid for a single flight leg."""
    landing_fee_usd: float = 0.0
    overnight_parking_usd: float = 0.0
    handling_fee_usd: float = 0.0
    customs_fee_usd: float = 0.0
    entry_date: Optional[date] = None
    notes: Optional[str] = None


class CostComparison(BaseModel):
    """Estimated vs actual cost comparison for a flight."""
    flight_id: str
    departure_airport: str
    arrival_airport: str
    estimated: ActualCostLineItems
    actual: ActualCostLineItems
    variances: ActualCostLineItems

    model_config = {"from_attributes": True}
