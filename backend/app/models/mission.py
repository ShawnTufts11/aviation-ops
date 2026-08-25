"""Mission, FlightLeg, ManifestEntry, and AircraftFuelProfile models."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MissionStatus(str, PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LegStatus(str, PyEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DIVERTED = "diverted"


class Mission(Base):
    """A multi-leg mission (e.g., MYNN → MTPP → MDPP → MYNN)."""

    __tablename__ = "missions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    aircraft_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("aircraft.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[MissionStatus] = mapped_column(
        Enum(MissionStatus, name="mission_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=MissionStatus.DRAFT,
        nullable=False,
    )
    pilot_in_command: Mapped[str | None] = mapped_column(String(36), nullable=True)
    second_in_command: Mapped[str | None] = mapped_column(String(36), nullable=True)

    mission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    home_base: Mapped[str] = mapped_column(String(10), default="MYNN", nullable=False)

    mission_number: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

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

    legs = relationship("FlightLeg", back_populates="mission", lazy="selectin",
                         cascade="all, delete-orphan",
                         order_by="FlightLeg.leg_number")

    def __repr__(self) -> str:
        return f"<Mission {self.id[:8]} ({self.status.value})>"


class FlightLeg(Base):
    """A single leg within a multi-leg mission."""

    __tablename__ = "flight_legs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    mission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leg_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Route
    departure_airport: Mapped[str] = mapped_column(String(10), nullable=False)
    arrival_airport: Mapped[str] = mapped_column(String(10), nullable=False)
    alternate_airport: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Times
    scheduled_departure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_departure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flight_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Distance
    distance_nm: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Fuel
    fuel_on_board_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    fuel_required_l: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Auto-calculated")

    # NOTAMs (manual entry Phase 1)
    notams: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[LegStatus] = mapped_column(
        Enum(LegStatus, name="leg_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=LegStatus.SCHEDULED,
        nullable=False,
    )

    # Compliance
    customs_clearance_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manifest_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    mission = relationship("Mission", back_populates="legs", lazy="selectin")
    manifest_entries = relationship("ManifestEntry", back_populates="leg", lazy="selectin",
                                     cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<FlightLeg {self.leg_number}: {self.departure_airport}→{self.arrival_airport}>"


class ManifestEntry(Base):
    """A passenger, crew member, or cargo item on a specific leg."""

    __tablename__ = "manifest_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    leg_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("flight_legs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_type: Mapped[str] = mapped_column(
        String(20), default="passenger", nullable=False
    )

    # Passenger details
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(2), nullable=True)
    passport_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    passport_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    id_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Leg tracking
    boarding_leg_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deplaning_leg_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cargo
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hazardous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    leg = relationship("FlightLeg", back_populates="manifest_entries", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ManifestEntry {self.full_name}>"


class AircraftFuelProfile(Base):
    """Configurable fuel burn profile per aircraft."""

    __tablename__ = "aircraft_fuel_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    aircraft_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("aircraft.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    cruise_burn_lph: Mapped[float] = mapped_column(Float, nullable=False, comment="L/hr at cruise")
    climb_burn_lph: Mapped[float | None] = mapped_column(Float, nullable=True)
    descent_burn_lph: Mapped[float | None] = mapped_column(Float, nullable=True)
    taxi_burn_lph: Mapped[float | None] = mapped_column(Float, nullable=True)
    cruise_speed_kt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reserve_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AircraftFuelProfile burn={self.cruise_burn_lph}L/hr>"
