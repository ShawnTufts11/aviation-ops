"""Pydantic schemas for leg cost logging and mission P&L."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Request schemas ──────────────────────────────────────────────


class LegCostCreate(BaseModel):
    """Request body to log a cost against a specific mission leg."""

    category: str = Field(..., description="fuel, handling, landing, customs, parking, misc")
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    payment_method: str = Field(default="cash", description="cash, credit, credit_card, wire")
    notes: str | None = None
    receipt_url: str | None = None


class LegCostUpdate(BaseModel):
    """Optional fields to patch on an existing cost record."""

    notes: str | None = None
    receipt_url: str | None = None


# ── Response schemas ─────────────────────────────────────────────


class LegCostResponse(BaseModel):
    """A single leg cost record as returned by the API."""

    id: str
    flight_leg_id: str
    category: str
    amount: float
    currency: str
    payment_method: str
    notes: str | None = None
    receipt_url: str | None = None
    logged_by: str | None = None
    logged_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Per-leg cost breakdown for a mission ────────────────────────


class LegCostSummary(BaseModel):
    """Cost summary for a single leg within a mission."""

    leg_number: int
    departure_airport: str
    arrival_airport: str
    status: str = "scheduled"
    estimated_cash_needed: float = 0.0
    actual_costs: list[LegCostResponse] = []
    total_actual: float = 0.0
    variance: float = 0.0  # actual - estimated


# ── Per-category breakdown ───────────────────────────────────────


class CategoryBreakdown(BaseModel):
    """Total actual costs broken down by category."""

    category: str
    total: float = 0.0
    count: int = 0


# ── P&L response ─────────────────────────────────────────────────


class MissionCostsResponse(BaseModel):
    """All leg costs for a mission, grouped by leg."""

    mission_id: str
    leg_count: int
    completed_leg_count: int = 0
    cancelled_leg_count: int = 0
    legs: list[LegCostSummary]


class MissionPnLResponse(BaseModel):
    """Real-time mission profit & loss summary."""

    mission_id: str
    total_estimated_costs: float = 0.0
    total_actual_costs: float = 0.0
    variance: float = 0.0
    per_category: list[CategoryBreakdown] = []
    leg_count: int
    completed_leg_count: int = 0
    cancelled_leg_count: int = 0
