"""
Airport model — ICAO-coded aerodrome data for route calculation, fuel planning,
customs/CIQ status, overflight compliance, and operational logistics.

Enriched with FBO options, hotel/accommodation data, maintenance capability,
fuel pricing, and structured runway/lights info for multi-leg international
mission planning.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text
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
    city: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="City served"
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

    # ── Runway & night ops ────────────────────────────────────────────────
    longest_runway_ft: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Length of longest runway (feet)"
    )
    runway_surface: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Surface type: asphalt, concrete, grass, gravel, water"
    )
    runway_info: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="Structured runway list: [{\"length_ft\", \"surface\", \"lighting\", \"width_ft\", \"ident\"}]"
    )
    has_night_ops: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Runway lighting / night operations available"
    )

    # ── Fuel ──────────────────────────────────────────────────────────────
    has_jet_a: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    has_avgas: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    fuel_price_jet_a_usd: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Avg Jet-A price (USD/gal) — last updated"
    )
    fuel_price_avgas_usd: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Avg Avgas price (USD/gal) — last updated"
    )
    fuel_last_updated: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="Date fuel prices last verified (YYYY-MM-DD)"
    )

    # ── Customs & compliance ──────────────────────────────────────────────
    has_customs: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="CIQ (Customs/Immigration/Quarantine) available"
    )
    customs_hours: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Customs operating hours (e.g. 24hr, by appointment, 0800-1700 local)"
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
        comment="Airport operating hours (e.g. 24hr, 0600-2200Z)"
    )

    # ── FBOs ──────────────────────────────────────────────────────────────
    fbo_options: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="FBO list: [{\"name\", \"phone\", \"frequency\", \"services\", \"fuel_prices\"}]"
    )

    # ── Accommodation & ground transport ──────────────────────────────────
    hotel_options: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="Hotels: [{\"name\", \"distance_miles\", \"shuttle\", \"phone\", \"notes\"}]"
    )
    ground_transport: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Ground transport: {\"rental_cars\": [...], \"taxi_available\": bool, \"ride_share\": bool, \"crew_car\": bool, \"notes\": str}"
    )

    # ── Maintenance capability ────────────────────────────────────────────
    maintenance_capability: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Maintenance: {\"on_site_mro\": bool, \"aircraft_types\": [...], \"engine_shop\": bool, \"avionics_shop\": bool, \"aog_support\": bool, \"contacts\": [...]}"
    )

    # ── Restrictions ──────────────────────────────────────────────────────
    restrictions: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="Known restrictions: [{\"type\", \"description\", \"source\", \"effective\"}]"
    )

    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Operational notes — free text for ops-specific concerns"
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    data_source: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="manual",
        comment="Source of this data: manual, ourairports, faa, openaip, etc."
    )
    last_verified: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="Date last verified by ops team (YYYY-MM-DD)"
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
