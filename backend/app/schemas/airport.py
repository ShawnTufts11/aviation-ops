"""
Pydantic schemas for airport data — used in route planning, fuel planning,
and compliance checks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AirportCreate(BaseModel):
    icao_code: str = Field(..., min_length=3, max_length=4, pattern=r"^[A-Za-z0-9]+$")
    iata_code: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timezone: str = "UTC"
    elevation_ft: Optional[int] = None
    country_code: str = Field(..., min_length=2, max_length=2)
    region: Optional[str] = None
    longest_runway_ft: Optional[int] = None
    runway_surface: Optional[str] = None
    has_jet_a: bool = False
    has_avgas: bool = False
    has_customs: bool = False
    has_landing_permit_required: bool = False
    has_overflight_permit_required: bool = False
    operating_hours: Optional[str] = None
    notes: Optional[str] = None


class AirportUpdate(BaseModel):
    iata_code: Optional[str] = None
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    elevation_ft: Optional[int] = None
    region: Optional[str] = None
    longest_runway_ft: Optional[int] = None
    runway_surface: Optional[str] = None
    has_jet_a: Optional[bool] = None
    has_avgas: Optional[bool] = None
    has_customs: Optional[bool] = None
    has_landing_permit_required: Optional[bool] = None
    has_overflight_permit_required: Optional[bool] = None
    operating_hours: Optional[str] = None
    notes: Optional[str] = None


class AirportResponse(BaseModel):
    icao_code: str
    iata_code: Optional[str] = None
    name: str
    latitude: float
    longitude: float
    timezone: str
    elevation_ft: Optional[int] = None
    country_code: str
    region: Optional[str] = None
    longest_runway_ft: Optional[int] = None
    runway_surface: Optional[str] = None
    has_jet_a: bool
    has_avgas: bool
    has_customs: bool
    has_landing_permit_required: bool
    has_overflight_permit_required: bool
    operating_hours: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AirportDistanceResponse(BaseModel):
    origin: AirportResponse
    destination: AirportResponse
    distance_nm: float
    distance_km: float
