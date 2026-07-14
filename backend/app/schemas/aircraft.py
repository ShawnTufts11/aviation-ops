"""Pydantic schemas for aircraft and component management."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Aircraft ─────────────────────────────────────────────────────

class AircraftCreate(BaseModel):
    tail_number: str = Field(..., min_length=1, max_length=20)
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1900, le=2030)
    serial_number: Optional[str] = None
    category: str = "single_engine_turboprop"
    mtow_kg: Optional[float] = None
    max_seats: int = 1
    max_cargo_kg: Optional[float] = None
    engine_type: Optional[str] = None
    engines: int = 1
    base: str = Field(..., min_length=3, max_length=10)
    home_airport: str = Field(..., min_length=3, max_length=10)
    country_reg: str = "BS"
    status: str = "active"


class AircraftUpdate(BaseModel):
    tail_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    status: Optional[str] = None
    base: Optional[str] = None
    home_airport: Optional[str] = None
    country_reg: Optional[str] = None
    registration_expiry: Optional[date] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    insurance_expiry: Optional[date] = None
    total_airframe_hours: Optional[float] = None
    total_cycles: Optional[int] = None


class AircraftResponse(BaseModel):
    id: str
    tail_number: str
    make: str
    model: str
    year: int
    serial_number: Optional[str] = None
    category: str
    status: str
    base: str
    home_airport: str
    country_reg: str
    registration_expiry: Optional[date] = None
    insurance_provider: Optional[str] = None
    insurance_expiry: Optional[date] = None
    mtow_kg: Optional[float] = None
    max_seats: int
    max_cargo_kg: Optional[float] = None
    total_airframe_hours: Optional[float] = None
    total_cycles: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Aircraft Component ───────────────────────────────────────────

class ComponentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    part_number: str = Field(..., min_length=1, max_length=100)
    serial_number: str = Field(..., min_length=1, max_length=100)
    component_type: str = "other"
    position: str = "n_a"
    installed_date: Optional[date] = None
    installed_hours: Optional[float] = None
    tbo_hours: Optional[float] = None
    tbo_cycles: Optional[int] = None
    tbo_calendar_days: Optional[int] = None
    life_limited: bool = False
    notes: Optional[str] = None


class ComponentResponse(BaseModel):
    id: str
    aircraft_id: str
    name: str
    part_number: str
    serial_number: str
    component_type: str
    position: str
    status: str
    installed_date: Optional[date] = None
    tbo_hours: Optional[float] = None
    life_limited: bool
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
