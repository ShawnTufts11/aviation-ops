"""Document model — compliance tracking for Part 135 operations."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentType(str, PyEnum):
    AIRWORTHINESS_CERT = "airworthiness_cert"
    REGISTRATION = "registration"
    INSURANCE = "insurance"
    OPERATING_SPECS = "operating_specs"
    OPUS_SPECS = "opus_specs"
    AOC = "aoc"
    NOISE_CERT = "noise_cert"
    EXPORT_CERT = "export_cert"
    DRY_LEASE = "dry_lease"
    CUSTOMS_CLEARANCE = "customs_clearance"
    LANDING_PERMIT = "landing_permit"
    OVERFLIGHT_PERMIT = "overflight_permit"
    CREW_LICENSE = "crew_license"
    MEDICAL = "medical"
    TRAINING_RECORD = "training_record"
    MAINTENANCE_MANUAL = "maintenance_manual"
    OPS_MANUAL = "ops_manual"
    MEL = "mel"
    INSURANCE_CERT = "insurance_cert"
    OTHER = "other"


class DocumentStatus(str, PyEnum):
    CURRENT = "current"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    aircraft_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("aircraft.id", ondelete="SET NULL"), nullable=True, index=True
    )
    crew_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("crew_members.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="doc_type", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    doc_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reminder_days: Mapped[int | None] = mapped_column(default=30, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="doc_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=DocumentStatus.CURRENT,
        nullable=False,
    )

    # Compliance tags — which countries/regulations this doc satisfies
    countries: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Comma-separated ISO country codes: BS,HT,US"
    )
    regulations: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Comma-separated: FAR-135,BCAA,OTAR"
    )

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

    def __repr__(self) -> str:
        return f"<Document {self.title} ({self.doc_type.value})>"
