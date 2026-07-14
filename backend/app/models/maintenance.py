"""MaintenanceTask model — tracks inspections, AD/SB compliance, and work orders."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MaintenanceTaskStatus(str, PyEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    DEFERRED = "deferred"


class MaintenanceTaskType(str, PyEnum):
    INSPECTION = "inspection"
    OIL_CHANGE = "oil_change"
    AD = "ad"
    SB = "sb"
    OVERHAUL = "overhaul"
    REPAIR = "repair"
    ANNUAL = "annual"
    HUNDRED_HOUR = "100hr"
    PHASE = "phase"


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    aircraft_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("aircraft.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[MaintenanceTaskType] = mapped_column(
        SAEnum(MaintenanceTaskType, name="maint_task_type", create_constraint=True),
        nullable=False,
    )
    status: Mapped[MaintenanceTaskStatus] = mapped_column(
        SAEnum(MaintenanceTaskStatus, name="maint_task_status", create_constraint=True),
        default=MaintenanceTaskStatus.SCHEDULED,
        nullable=False,
    )
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="AD/SB reference")
    interval_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    aircraft = relationship("Aircraft", backref="maintenance_tasks", lazy="selectin")

    def __repr__(self) -> str:
        return f"<MaintenanceTask {self.title} ({self.status})>"
