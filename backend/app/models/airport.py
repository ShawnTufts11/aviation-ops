"""
Airport model — ICAO-coded aerodrome data for route calculation, fuel planning,
customs/CIQ status, and overflight compliance.

Supports the Route Performance Calculator by providing coordinates for great-circle
distance, runway data for aircraft capability checks, and customs/permit flags for
international trip planning.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Airport(Base):
    """An aerodrome identified by ICAO code — the atomic unit of route planning."""

    __tablename__ = "airports"

    icao_code: Mapped[str] = mapped_column(
        String(4), primary_key=True, comment="ICAO airport code (e.g. MYNN)"
    )
    iata_code: Mapped[str | None] = mapped_column(
        String(3), nullable=True, comment="IATA code (e.g. NAS)"
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Full airport name"
    )
    latitude: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Decimal degrees (positive = North)"
    )
    longitude: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Decimal degrees (positive = East)"
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="UTC",
        comment="IANA timezone (e.g. America/Nassau)"
    )
    elevation_ft: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Elevation above MSL (feet)"
    )
    country_code: Mapped[str] = mapped_column(
        String(2), nullable=False, comment="ISO 3166-1 alpha-2 country code"
    )
    region: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Region/state/province (e.g. New Providence)"
    )

    # ── Runway ────────────────────────────────────────────────────────────
    longest_runway_ft: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Length of longest runway (feet)"
    )
    runway_surface: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Surface type: asphalt, concrete, grass, gravel, water"
    )

    # ── Fuel ──────────────────────────────────────────────────────────────
    has_jet_a: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    has_avgas: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # ── Customs & compliance ──────────────────────────────────────────────
    has_customs: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="CIQ (Customs/Immigration/Quarantine) available"
    )
    has_landing_permit_required: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Prior landing permit required (e.g. Cuba, Bahamas)"
    )
    has_overflight_permit_required: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Overflight permit required for entry"
    )
    operating_hours: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Operating hours (e.g. 24hr, 0600-2200Z)"
    )

    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Operational notes — restrictions, warnings"
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

    def __repr__(self) -> str:
        return f"<Airport {self.icao_code} ({self.name})>"
