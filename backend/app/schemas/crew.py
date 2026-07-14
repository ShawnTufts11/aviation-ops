"""Pydantic schemas for crew management."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class CrewCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "first_officer"
    license_type: Optional[str] = None
    license_number: Optional[str] = None
    license_country: Optional[str] = None
    license_expiry: Optional[date] = None
    medical_class: Optional[str] = None
    medical_expiry: Optional[date] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    base_airport: Optional[str] = None
    date_of_hire: Optional[date] = None
    notes: Optional[str] = None


class CrewUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    license_type: Optional[str] = None
    license_number: Optional[str] = None
    license_expiry: Optional[date] = None
    medical_class: Optional[str] = None
    medical_expiry: Optional[date] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    base_airport: Optional[str] = None
    notes: Optional[str] = None


class QualificationCreate(BaseModel):
    qual_type: str
    aircraft_type: Optional[str] = None
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class QualificationResponse(BaseModel):
    id: str
    crew_id: str
    qual_type: str
    status: str
    aircraft_type: Optional[str] = None
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrewResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    display_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    status: str
    license_type: Optional[str] = None
    license_number: Optional[str] = None
    license_country: Optional[str] = None
    license_expiry: Optional[date] = None
    medical_class: Optional[str] = None
    medical_expiry: Optional[date] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    base_airport: Optional[str] = None
    date_of_hire: Optional[date] = None
    last_90d_hours: Optional[float] = None
    last_12m_hours: Optional[float] = None
    last_flight_date: Optional[date] = None
    last_proficiency_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    qualifications: list[QualificationResponse] = []

    model_config = {"from_attributes": True}
