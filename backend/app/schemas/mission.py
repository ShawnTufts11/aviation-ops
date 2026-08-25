"""Multi-leg mission schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ManifestEntryCreate(BaseModel):
    entry_type: str = "passenger"
    full_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    id_number: Optional[str] = None
    weight_kg: Optional[float] = None
    boarding_leg_number: Optional[int] = None
    deplaning_leg_number: Optional[int] = None
    description: Optional[str] = None
    hazardous: bool = False
    notes: Optional[str] = None


class ManifestEntryResponse(BaseModel):
    id: str
    leg_id: str
    entry_type: str
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    weight_kg: Optional[float] = None
    boarding_leg_number: Optional[int] = None
    deplaning_leg_number: Optional[int] = None
    description: Optional[str] = None
    hazardous: bool = False
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class LegCreate(BaseModel):
    leg_number: int = Field(..., ge=1)
    departure_airport: str = Field(..., min_length=3, max_length=10)
    arrival_airport: str = Field(..., min_length=3, max_length=10)
    alternate_airport: Optional[str] = None
    scheduled_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None
    distance_nm: Optional[int] = None
    fuel_on_board_l: Optional[float] = None
    notams: Optional[str] = None


class LegUpdate(BaseModel):
    status: Optional[str] = None
    scheduled_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    fuel_on_board_l: Optional[float] = None
    notams: Optional[str] = None
    notes: Optional[str] = None


class LegResponse(BaseModel):
    id: str
    mission_id: str
    leg_number: int
    departure_airport: str
    arrival_airport: str
    alternate_airport: Optional[str] = None
    scheduled_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    flight_time_minutes: Optional[int] = None
    distance_nm: Optional[int] = None
    fuel_on_board_l: Optional[float] = None
    fuel_required_l: Optional[float] = None
    notams: Optional[str] = None
    status: str
    notes: Optional[str] = None
    manifest_entries: list[ManifestEntryResponse] = []

    model_config = {"from_attributes": True}


class MissionCreate(BaseModel):
    aircraft_id: Optional[str] = None
    pilot_in_command: Optional[str] = None
    second_in_command: Optional[str] = None
    mission_date: Optional[date] = None
    home_base: str = "MYNN"
    notes: Optional[str] = None


class MissionUpdate(BaseModel):
    aircraft_id: Optional[str] = None
    status: Optional[str] = None
    pilot_in_command: Optional[str] = None
    second_in_command: Optional[str] = None
    notes: Optional[str] = None


class MissionResponse(BaseModel):
    id: str
    aircraft_id: Optional[str] = None
    status: str
    pilot_in_command: Optional[str] = None
    second_in_command: Optional[str] = None
    mission_date: Optional[date] = None
    home_base: str
    mission_number: Optional[str] = None
    notes: Optional[str] = None
    legs: list[LegResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class FuelProfileCreate(BaseModel):
    cruise_burn_lph: float = Field(..., gt=0)
    climb_burn_lph: Optional[float] = None
    descent_burn_lph: Optional[float] = None
    taxi_burn_lph: Optional[float] = None
    cruise_speed_kt: Optional[int] = None
    reserve_minutes: int = 45


class FuelProfileResponse(BaseModel):
    id: str
    aircraft_id: str
    cruise_burn_lph: float
    climb_burn_lph: Optional[float] = None
    cruise_speed_kt: Optional[int] = None
    reserve_minutes: int

    model_config = {"from_attributes": True}
