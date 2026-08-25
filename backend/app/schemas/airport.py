"""
Pydantic schemas for airport data — route planning, fuel planning,
compliance checks, and operational logistics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AirportCreate(BaseModel):
    icao_code: str = Field(..., min_length=3, max_length=4, pattern=r"^[A-Za-z0-9]+$")
    iata_code: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    city: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timezone: str = "UTC"
    elevation_ft: Optional[int] = None
    country_code: str = Field(..., min_length=2, max_length=2)
    region: Optional[str] = None

    # Runway & night ops
    longest_runway_ft: Optional[int] = None
    runway_surface: Optional[str] = None
    runway_info: Optional[list] = None
    has_night_ops: bool = False

    # Fuel
    has_jet_a: bool = False
    has_avgas: bool = False
    fuel_price_jet_a_usd: Optional[float] = None
    fuel_price_avgas_usd: Optional[float] = None
    fuel_last_updated: Optional[str] = None

    # Cost fields (landing, parking, handling, customs, overflight)
    landing_fee_usd: Optional[float] = None
    overnight_parking_usd: Optional[float] = None
    handling_fee_usd: Optional[float] = None
    customs_fee_usd: Optional[float] = None
    overflight_permit_cost_usd: Optional[float] = None
    payment_type: Optional[str] = "mixed"
    landing_notes: Optional[str] = None

    # Customs & compliance
    has_customs: bool = False
    customs_hours: Optional[str] = None
    has_landing_permit_required: bool = False
    has_overflight_permit_required: bool = False
    operating_hours: Optional[str] = None

    # FBOs
    fbo_options: Optional[list] = None

    # Accommodation & transport
    hotel_options: Optional[list] = None
    ground_transport: Optional[dict] = None

    # Maintenance
    maintenance_capability: Optional[dict] = None

    # Restrictions
    restrictions: Optional[list] = None

    notes: Optional[str] = None
    data_source: Optional[str] = "manual"
    last_verified: Optional[str] = None


class AirportUpdate(BaseModel):
    iata_code: Optional[str] = None
    name: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    elevation_ft: Optional[int] = None
    region: Optional[str] = None
    longest_runway_ft: Optional[int] = None
    runway_surface: Optional[str] = None
    runway_info: Optional[list] = None
    has_night_ops: Optional[bool] = None
    has_jet_a: Optional[bool] = None
    has_avgas: Optional[bool] = None
    fuel_price_jet_a_usd: Optional[float] = None
    fuel_price_avgas_usd: Optional[float] = None
    fuel_last_updated: Optional[str] = None
    landing_fee_usd: Optional[float] = None
    overnight_parking_usd: Optional[float] = None
    handling_fee_usd: Optional[float] = None
    customs_fee_usd: Optional[float] = None
    overflight_permit_cost_usd: Optional[float] = None
    payment_type: Optional[str] = None
    landing_notes: Optional[str] = None
    has_customs: Optional[bool] = None
    customs_hours: Optional[str] = None
    has_landing_permit_required: Optional[bool] = None
    has_overflight_permit_required: Optional[bool] = None
    operating_hours: Optional[str] = None
    fbo_options: Optional[list] = None
    hotel_options: Optional[list] = None
    ground_transport: Optional[dict] = None
    maintenance_capability: Optional[dict] = None
    restrictions: Optional[list] = None
    notes: Optional[str] = None
    data_source: Optional[str] = None
    last_verified: Optional[str] = None


class AirportResponse(BaseModel):
    icao_code: str
    iata_code: Optional[str] = None
    name: str
    city: Optional[str] = None
    latitude: float
    longitude: float
    timezone: str
    elevation_ft: Optional[int] = None
    country_code: str
    region: Optional[str] = None

    # Runway & night ops
    longest_runway_ft: Optional[int] = None
    runway_surface: Optional[str] = None
    runway_info: Optional[list] = None
    has_night_ops: bool

    # Fuel
    has_jet_a: bool
    has_avgas: bool
    fuel_price_jet_a_usd: Optional[float] = None
    fuel_price_avgas_usd: Optional[float] = None
    fuel_last_updated: Optional[str] = None

    # Cost fields (landing, parking, handling, customs, overflight)
    landing_fee_usd: Optional[float] = None
    overnight_parking_usd: Optional[float] = None
    handling_fee_usd: Optional[float] = None
    customs_fee_usd: Optional[float] = None
    overflight_permit_cost_usd: Optional[float] = None
    payment_type: Optional[str] = None
    landing_notes: Optional[str] = None

    # Customs & compliance
    has_customs: bool
    customs_hours: Optional[str] = None
    has_landing_permit_required: bool
    has_overflight_permit_required: bool
    operating_hours: Optional[str] = None

    # FBOs
    fbo_options: Optional[list] = None

    # Accommodation & transport
    hotel_options: Optional[list] = None
    ground_transport: Optional[dict] = None

    # Maintenance
    maintenance_capability: Optional[dict] = None

    # Restrictions
    restrictions: Optional[list] = None

    notes: Optional[str] = None
    data_source: Optional[str] = None
    last_verified: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AirportDistanceResponse(BaseModel):
    origin: AirportResponse
    destination: AirportResponse
    distance_nm: float
    distance_km: float
