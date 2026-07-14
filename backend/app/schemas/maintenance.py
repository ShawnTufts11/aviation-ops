"""Pydantic schemas for maintenance task management."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class MaintenanceCreate(BaseModel):
    aircraft_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: str = "inspection"
    reference: Optional[str] = None
    interval_hours: Optional[float] = None
    interval_days: Optional[int] = None
    scheduled_date: Optional[date] = None


class MaintenanceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    scheduled_date: Optional[date] = None
    completed_date: Optional[datetime] = None
    completed_hours: Optional[float] = None
    completed_cycles: Optional[int] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None
    reference: Optional[str] = None


class MaintenanceResponse(BaseModel):
    id: str
    aircraft_id: str
    title: str
    description: Optional[str] = None
    task_type: str
    status: str
    reference: Optional[str] = None
    interval_hours: Optional[float] = None
    interval_days: Optional[int] = None
    scheduled_date: Optional[date] = None
    completed_date: Optional[datetime] = None
    completed_hours: Optional[float] = None
    completed_cycles: Optional[int] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MaintenanceListResponse(BaseModel):
    data: list[MaintenanceResponse]
    total: int
    page: int
    per_page: int
    overdue_count: int
    due_soon_count: int
