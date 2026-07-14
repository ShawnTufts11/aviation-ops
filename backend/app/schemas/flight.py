"""Pydantic schemas for flight operations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class FlightCreate(BaseModel):
    aircraft_id: Optional[str] = None
    flight_number: Optional[str] = None
    flight_type: str = "charter"
    departure_airport: str = Field(..., min_length=3, max_length=10)
    arrival_airport: str = Field(..., min_length=3, max_length=10)
    alternate_airport: Optional[str] = None
    scheduled_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None
    pilot_in_command: Optional[str] = None
    second_in_command: Optional[str] = None
    passengers_count: Optional[int] = None
    cargo_weight_kg: Optional[float] = None
    notes: Optional[str] = None


class FlightUpdate(BaseModel):
    status: Optional[str] = None
    aircraft_id: Optional[str] = None
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    flight_time_hours: Optional[float] = None
    fuel_burned_liters: Optional[float] = None
    pilot_in_command: Optional[str] = None
    second_in_command: Optional[str] = None
    passengers_count: Optional[int] = None
    cargo_weight_kg: Optional[float] = None
    notes: Optional[str] = None
    flight_number: Optional[str] = None


class FlightResponse(BaseModel):
    id: str
    aircraft_id: Optional[str] = None
    flight_number: Optional[str] = None
    flight_type: str
    status: str
    departure_airport: str
    arrival_airport: str
    alternate_airport: Optional[str] = None
    scheduled_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    flight_time_hours: Optional[float] = None
    fuel_burned_liters: Optional[float] = None
    pilot_in_command: Optional[str] = None
    second_in_command: Optional[str] = None
    passengers_count: Optional[int] = None
    cargo_weight_kg: Optional[float] = None
    customs_clearance_ref: Optional[str] = None
    revenue: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RouteCreate(BaseModel):
    departure: str = Field(..., min_length=3, max_length=10)
    arrival: str = Field(..., min_length=3, max_length=10)
    route_type: str = "domestic"
    distance_nm: Optional[int] = None
    flight_time_mins: Optional[int] = None


class RouteResponse(BaseModel):
    id: str
    departure: str
    arrival: str
    route_type: str
    distance_nm: Optional[int] = None
    flight_time_mins: Optional[int] = None

    model_config = {"from_attributes": True}
