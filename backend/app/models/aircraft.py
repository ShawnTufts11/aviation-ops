"""
Aircraft and AircraftComponent models — the core asset registry for Part 135 ops.

Matches the SPEC.md data model exactly:
  - Aircraft: tail_number, make, model, category, MTOW, seats, status, insurance, etc.
  - AircraftComponent: tracked sub-assemblies with TBO/hours/life-limited fields.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ──────────────────────────────────────────────────────────────────


class AircraftCategory(str, PyEnum):
    """FAA / ICAO aircraft category codes relevant to Part 135."""
    SINGLE_ENGINE_PISTON = "single_engine_piston"
    MULTI_ENGINE_PISTON = "multi_engine_piston"
    SINGLE_ENGINE_TURBOPROP = "single_engine_turboprop"
    MULTI_ENGINE_TURBOPROP = "multi_engine_turboprop"
    LIGHT_JET = "light_jet"
    MIDSIZE_JET = "midsize_jet"
    SUPER_MIDSIZE_JET = "super_midsize_jet"
    HEAVY_JET = "heavy_jet"
    ROTORCRAFT = "rotorcraft"


class AircraftStatus(str, PyEnum):
    """Operational status of an aircraft."""
    ACTIVE = "active"
    IN_MAINTENANCE = "in_maintenance"
    GROUNDED = "grounded"
    RETIRED = "retired"
    STORED = "stored"


class ComponentPosition(str, PyEnum):
    """Where the component is installed on the aircraft."""
    LEFT = "left"
    RIGHT = "right"
    NOSE = "nose"
    TAIL = "tail"
    CENTER = "center"
    BOTH = "both"
    N_A = "n_a"


class ComponentType(str, PyEnum):
    """Types of tracked aircraft components."""
    ENGINE = "engine"
    PROPELLER = "propeller"
    LANDING_GEAR = "landing_gear"
    BATTERY = "battery"
    AVIONICS = "avionics"
    APU = "apu"
    HYDRAULIC = "hydraulic"
    OTHER = "other"


class ComponentStatus(str, PyEnum):
    """Serviceability status of a component."""
    SERVICEABLE = "serviceable"
    OVERHAUL_DUE = "overhaul_due"
    OVERHAULED = "overhauled"
    REMOVED = "removed"
    DAMAGED = "damaged"


# ── Aircraft ───────────────────────────────────────────────────────────────


class Aircraft(Base):
    __tablename__ = "aircraft"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identification ────────────────────────────────────────────────────
    tail_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    serial_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    category: Mapped[AircraftCategory] = mapped_column(
        Enum(AircraftCategory, name="aircraft_category", create_constraint=True),
        nullable=False,
    )

    # ── Weights & capacities ──────────────────────────────────────────────
    mtow_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True, comment="Maximum Take-Off Weight (kg)"
    )
    mlw_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True, comment="Maximum Landing Weight (kg)"
    )
    bhw_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True, comment="Basic Empty Weight (kg)"
    )
    max_seats: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Maximum passenger seats"
    )
    max_cargo_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    fuel_capacity_l: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    # ── Performance ───────────────────────────────────────────────────────
    cruise_speed_kt: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Typical cruise speed (knots TAS)"
    )
    cruise_fuel_flow_gph: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 1), nullable=True, comment="Fuel burn at typical cruise (gal/hr)"
    )
    typical_cruise_alt_ft: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Typical cruise altitude (feet MSL)"
    )

    # ── Climb / Descent ───────────────────────────────────────────────────
    climb_speed_kt: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Best rate climb speed (KIAS)"
    )
    climb_rate_fpm: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Average climb rate (ft/min)"
    )
    descent_speed_kt: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Typical descent speed (KIAS)"
    )
    taxi_fuel_gallons: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 1), nullable=True, default=5.0,
        comment="Estimated taxi fuel burn (gallons)"
    )

    # ── Range & reserves ──────────────────────────────────────────────────
    range_nm: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Maximum range (nm, no reserves)"
    )
    max_range_with_reserves_nm: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Practical range with FAR 135 reserves"
    )
    service_ceiling_ft: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    reserve_fuel_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=45,
        comment="Fuel reserve requirement in minutes (FAR 135 default 45)"
    )

    # ── Operational capabilities ──────────────────────────────────────────
    overwater_capable: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Equipped for extended overwater (life rafts, ELT, etc.)"
    )
    known_icing_certified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Certified for flight in known icing conditions"
    )
    rnp_approach_capable: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Capable of RNP/RNAV approach procedures"
    )
    rvsm_capable: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="RVSM certified (reduced vertical separation)"
    )
    autopilot_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="basic",
        comment="Autopilot capability: none, basic, coupled, fms"
    )
    deice_equipped: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Has de-icing boots / heated surfaces"
    )

    # ── Status ────────────────────────────────────────────────────────────
    status: Mapped[AircraftStatus] = mapped_column(
        Enum(AircraftStatus, name="aircraft_status", create_constraint=True),
        default=AircraftStatus.ACTIVE,
        nullable=False,
    )

    # ── Base & home ───────────────────────────────────────────────────────
    base: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="ICAO code of base airport"
    )
    home_airport: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="Primary home ICAO"
    )
    country_reg: Mapped[str] = mapped_column(
        String(2), default="BS", nullable=False, comment="Registration country code"
    )

    # ── Registration & compliance ─────────────────────────────────────────
    registration_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    airworthiness_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    coa_expiry: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Certificate of Airworthiness expiry"
    )

    # ── Insurance ─────────────────────────────────────────────────────────
    insurance_provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    insurance_policy_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    insurance_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    insurance_coverage_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )

    # ── Hour tracking ─────────────────────────────────────────────────────
    total_airframe_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, default=0
    )
    total_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)

    # ── Metadata ──────────────────────────────────────────────────────────
    extra_metadata: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False, comment="Flexible extra fields"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────
    organization = relationship("Organization", back_populates="aircraft", lazy="selectin")
    components = relationship(
        "AircraftComponent",
        back_populates="aircraft",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Aircraft {self.tail_number} ({self.make} {self.model})>"


# ── AircraftComponent ──────────────────────────────────────────────────────


class AircraftComponent(Base):
    __tablename__ = "aircraft_components"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    aircraft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("aircraft.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identification ────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Component name (e.g. 'Left Engine')"
    )
    part_number: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    serial_number: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    position: Mapped[ComponentPosition] = mapped_column(
        Enum(ComponentPosition, name="component_position", create_constraint=True),
        default=ComponentPosition.N_A,
        nullable=False,
    )
    component_type: Mapped[ComponentType] = mapped_column(
        Enum(ComponentType, name="component_type", create_constraint=True),
        nullable=False,
    )

    # ── Installation ──────────────────────────────────────────────────────
    installed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    installed_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True,
        comment="Airframe hours at installation",
    )

    # ── TBO / Life limits ──────────────────────────────────────────────────
    tbo_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True,
        comment="Time Between Overhaul (hours)",
    )
    tbo_cycles: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Time Between Overhaul (cycles)",
    )
    tbo_calendar_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="TBO calendar limit (days)",
    )
    hours_since_overhaul: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, default=0
    )
    cycles_since_overhaul: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    life_limited: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True if this is a life-limited part (LLP)",
    )
    life_limit_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    life_limit_cycles: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # ── Status ────────────────────────────────────────────────────────────
    status: Mapped[ComponentStatus] = mapped_column(
        Enum(ComponentStatus, name="component_status", create_constraint=True),
        default=ComponentStatus.SERVICEABLE,
        nullable=False,
    )
    last_overhaul_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────
    aircraft = relationship("Aircraft", back_populates="components", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AircraftComponent {self.name} ({self.part_number})>"
