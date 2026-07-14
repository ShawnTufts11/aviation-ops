"""Flight and Route models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FlightType(str, PyEnum):
    PASSENGER = "passenger"
    CARGO = "cargo"
    FERRY = "ferry"
    POSITIONING = "positioning"
    TRAINING = "training"
    CHARTER = "charter"


class FlightStatus(str, PyEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DIVERTED = "diverted"


class Flight(Base):
    __tablename__ = "flights"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    aircraft_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("aircraft.id", ondelete="SET NULL"), nullable=True, index=True
    )
    flight_number: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    flight_type: Mapped[FlightType] = mapped_column(
        Enum(FlightType, name="flight_type", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=FlightType.CHARTER,
        nullable=False,
    )
    status: Mapped[FlightStatus] = mapped_column(
        Enum(FlightStatus, name="flight_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=FlightStatus.SCHEDULED,
        nullable=False,
    )

    # Route
    departure_airport: Mapped[str] = mapped_column(String(10), nullable=False)
    arrival_airport: Mapped[str] = mapped_column(String(10), nullable=False)
    alternate_airport: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Times
    scheduled_departure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_departure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Flight data
    flight_time_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    cycles: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)
    fuel_burned_liters: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Crew (denormalized IDs for quick reference)
    pilot_in_command: Mapped[str | None] = mapped_column(String(36), nullable=True)
    second_in_command: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Pax & cargo
    passengers_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cargo_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Compliance
    customs_clearance_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manifest_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Financial
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    fuel_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

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
    aircraft = relationship("Aircraft", backref="flights", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Flight {self.flight_number or self.id[:8]} {self.departure_airport}→{self.arrival_airport}>"


class Route(Base):
    """Frequently flown routes for quick flight creation."""

    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    departure: Mapped[str] = mapped_column(String(10), nullable=False)
    arrival: Mapped[str] = mapped_column(String(10), nullable=False)
    route_type: Mapped[str] = mapped_column(
        String(20), default="domestic", nullable=False
    )
    distance_nm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flight_time_mins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Route {self.departure}→{self.arrival}>"
