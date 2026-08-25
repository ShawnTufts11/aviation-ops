"""
FlightRelease model — the formal Part 135 flight release document.

Contains all fields required for a compliant flight release: route, crew,
fuel planning, maintenance control, weather brief, NOTAMs, gripes, PIC
acceptance, signature blocks, and hot-zone assessment.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ──────────────────────────────────────────────────────────────────


class ReleaseStatus(str, PyEnum):
    """Lifecycle status of a flight release."""
    DRAFT = "draft"
    IN_MAINTENANCE = "in_maintenance"
    RELEASED = "released"
    AMENDED = "amended"
    CLOSED = "closed"


class MissionCapability(str, PyEnum):
    """Declared mission capability per maintenance control."""
    FULL = "full"
    PARTIAL = "partial"
    NOT_CAPABLE = "not_capable"


class DestinationRisk(str, PyEnum):
    """Hot-zone destination risk assessment."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class GroundSecurity(str, PyEnum):
    """Ground security assessment for the destination."""
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH_THREAT = "high_threat"
    CRITICAL = "critical"


class CustomsStatus(str, PyEnum):
    """Customs clearance status for international legs."""
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    CLEARED = "cleared"
    DENIED = "denied"


# ── FlightRelease ──────────────────────────────────────────────────────────


class FlightRelease(Base):
    """A formal Part 135 flight release document."""

    __tablename__ = "flight_releases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Release identification ────────────────────────────────────────────
    release_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True,
        comment="Auto-generated release number (FR-YYYY-NNN), set by service layer",
    )
    status: Mapped[ReleaseStatus] = mapped_column(
        Enum(ReleaseStatus, name="release_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=ReleaseStatus.DRAFT,
        nullable=False,
    )
    mission_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Optional mission / trip name"
    )

    # ── Route ─────────────────────────────────────────────────────────────
    aircraft_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("aircraft.id", ondelete="SET NULL"), nullable=True, index=True
    )
    origin_icao: Mapped[str] = mapped_column(String(10), nullable=False)
    dest_icao: Mapped[str] = mapped_column(String(10), nullable=False)
    alternate_icao: Mapped[str | None] = mapped_column(String(10), nullable=True)
    departure_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    est_enroute_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Route waypoints (JSON array) ───────────────────────────────────────
    route_waypoints: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list,
        comment="Ordered list of route waypoints as [{lat, lon, ident, alt, ...}]",
    )

    # ── Crew ───────────────────────────────────────────────────────────────
    pic_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="Pilot In Command user ID"
    )
    sic_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="Second In Command user ID"
    )

    # ── Duty tracking ──────────────────────────────────────────────────────
    pic_duty_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="PIC duty period start (UTC)",
    )
    pic_duty_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="PIC duty period end (UTC)",
    )
    sic_duty_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="SIC duty period start (UTC)",
    )
    sic_duty_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="SIC duty period end (UTC)",
    )

    # ── Weather brief (JSON) ───────────────────────────────────────────────
    weather_brief: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict,
        comment="Weather brief per airport: {icao: {metar: ..., taf: ...}}",
    )

    # ── NOTAM references ───────────────────────────────────────────────────
    notam_refs: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list,
        comment="Array of NOTAM references / identifiers",
    )

    # ── Fuel plan (lbs) ────────────────────────────────────────────────────
    ramp_fuel_lbs: Mapped[float | None] = mapped_column(Float, nullable=True, default=0)
    trip_fuel_lbs: Mapped[float | None] = mapped_column(Float, nullable=True, default=0)
    contingency_fuel_lbs: Mapped[float | None] = mapped_column(Float, nullable=True, default=0)
    alternate_fuel_lbs: Mapped[float | None] = mapped_column(Float, nullable=True, default=0)
    reserve_fuel_lbs: Mapped[float | None] = mapped_column(Float, nullable=True, default=0)
    arrival_fuel_lbs: Mapped[float | None] = mapped_column(Float, nullable=True, default=0)
    fuel_legal: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True if fuel plan meets all regulatory requirements",
    )

    # ── Maintenance control ────────────────────────────────────────────────
    safe_for_flight: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    safe_for_flight_signed_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Name/ID of maintenance who signed safe-for-flight",
    )
    safe_for_flight_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp of safe-for-flight signature",
    )
    maintenance_signed_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Name/ID of maintenance personnel who signed",
    )
    maintenance_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mission_capability: Mapped[MissionCapability] = mapped_column(
        Enum(MissionCapability, name="mission_capability", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=MissionCapability.FULL,
        nullable=False,
    )
    maintenance_restrictions: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict,
        comment="Maintenance restrictions / MEL items as JSON",
    )

    # ── Gripes ─────────────────────────────────────────────────────────────
    gripes_open: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list,
        comment="Array of open gripes [{id, description, reported_at, ...}]",
    )
    gripes_deferred: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list,
        comment="Array of deferred gripes [{id, description, deferred_by, ...}]",
    )

    # ── PIC acceptance ─────────────────────────────────────────────────────
    pic_acceptance: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="PIC acceptance statement or notes",
    )

    # ── Signature blocks ───────────────────────────────────────────────────
    pic_accepted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True when PIC has accepted the aircraft after maintenance sign-off",
    )
    pic_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp of PIC acceptance",
    )
    pic_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dispatcher_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
        comment="User ID of reviewer who last reviewed this release",
    )

    # ── PIC rejection / send-back-to-maintenance ─────────────────────────
    pic_rejected: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True when PIC rejects the aircraft after maintenance sign-off, sending it back",
    )
    pic_rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp of PIC rejection",
    )
    pic_rejected_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Name/ID of PIC who rejected",
    )
    pic_rejection_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Reason for PIC rejection (gripe description)",
    )

    # ── Hot-zone assessment ────────────────────────────────────────────────
    destination_risk: Mapped[DestinationRisk | None] = mapped_column(
        Enum(DestinationRisk, name="destination_risk", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        comment="Destination risk level for hot-zone / threat assessment",
    )
    ground_security: Mapped[GroundSecurity | None] = mapped_column(
        Enum(GroundSecurity, name="ground_security", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        comment="Ground security assessment at destination",
    )
    overwater_legs: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True if any leg is overwater (beyond gliding distance)",
    )
    etp_waypoint: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="Equal Time Point waypoint identifier for overwater legs",
    )
    customs_status: Mapped[CustomsStatus | None] = mapped_column(
        Enum(CustomsStatus, name="customs_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        comment="Customs clearance status for international operations",
    )

    # ── Metadata timestamps ────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    amended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp of last amendment",
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp when release was closed",
    )

    # ── Relationships ─────────────────────────────────────────────────────
    aircraft = relationship("Aircraft", backref="flight_releases", lazy="selectin")

    def __repr__(self) -> str:
        return f"<FlightRelease {self.release_number} ({self.status.value})>"
