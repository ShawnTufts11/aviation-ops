"""Pilot logbook model — auto-created from completed flights."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PilotLogEntry(Base):
    """A single logbook entry, auto-created when a flight leg completes."""

    __tablename__ = "pilot_logbook"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crew_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("crew_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    flight_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("flights.id", ondelete="SET NULL"), nullable=True
    )
    mission_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("missions.id", ondelete="SET NULL"), nullable=True
    )
    aircraft_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("aircraft.id", ondelete="CASCADE"), nullable=False
    )

    # Flight data
    flight_date: Mapped[date] = mapped_column(Date, nullable=False)
    departure_airport: Mapped[str] = mapped_column(String(10), nullable=False)
    arrival_airport: Mapped[str] = mapped_column(String(10), nullable=False)
    aircraft_tail: Mapped[str] = mapped_column(String(20), nullable=False)
    aircraft_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Times
    flight_time_hours: Mapped[float] = mapped_column(Float, nullable=False)
    day_landings: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    night_landings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    instrument_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    night_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    cross_country: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Role
    pic: Mapped[bool] = mapped_column(default=True, nullable=False)
    sic: Mapped[bool] = mapped_column(default=False, nullable=False)
    dual: Mapped[bool] = mapped_column(default=False, nullable=False)
    instructor: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Remarks (pilot-editable)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_generated: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<LogEntry {self.aircraft_tail} {self.departure_airport}→{self.arrival_airport}>"
