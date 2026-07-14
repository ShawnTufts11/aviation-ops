"""Pydantic schemas for compliance documents."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    doc_type: str
    doc_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    reminder_days: int = 30
    file_url: Optional[str] = None
    aircraft_id: Optional[str] = None
    crew_id: Optional[str] = None
    countries: Optional[str] = Field(None, description="Comma-separated ISO codes: BS,HT,US")
    regulations: Optional[str] = Field(None, description="Comma-separated: FAR-135,BCAA,OTAR")
    notes: Optional[str] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    file_url: Optional[str] = None
    countries: Optional[str] = None
    regulations: Optional[str] = None
    notes: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    title: str
    doc_type: str
    doc_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    reminder_days: Optional[int] = None
    file_url: Optional[str] = None
    status: str
    aircraft_id: Optional[str] = None
    crew_id: Optional[str] = None
    countries: Optional[str] = None
    regulations: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
