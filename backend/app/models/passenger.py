"""Passenger model — repeat client database for eAPIS and manifests."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Passenger(Base):
    """Repeat passenger profile — feeds manifests and eAPIS export."""

    __tablename__ = "passengers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Identity
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # ID / Travel docs (UNIQUE — no duplicates across org)
    passport_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True
    )
    passport_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    id_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="National ID / SSN"
    )
    ssn: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="US SSN (encrypted in prod)"
    )

    # Contact
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Profile
    weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Flight tracking
    total_flights: Mapped[int] = mapped_column(default=0, nullable=False)
    first_flight: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_flight: Mapped[date | None] = mapped_column(Date, nullable=True)

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
        return f"<Passenger {self.full_name} ({self.nationality})>"
