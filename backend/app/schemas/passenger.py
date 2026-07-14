"""Passenger database schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class PassengerCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    id_number: Optional[str] = None
    ssn: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None


class PassengerUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    id_number: Optional[str] = None
    ssn: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None


class PassengerResponse(BaseModel):
    id: str
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None
    total_flights: int
    first_flight: Optional[date] = None
    last_flight: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}
