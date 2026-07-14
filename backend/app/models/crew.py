"""CrewMember and CrewQualification models."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CrewRole(str, PyEnum):
    CAPTAIN = "captain"
    FIRST_OFFICER = "first_officer"
    SIC = "sic"
    MECHANIC = "mechanic"
    FLIGHT_ATTENDANT = "flight_attendant"
    DISPATCHER = "dispatcher"


class CrewStatus(str, PyEnum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TRAINING = "training"
    SICK = "sick"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class LicenseType(str, PyEnum):
    ATPL = "atpl"
    CPL = "cpl"
    PPL = "ppl"
    MECHANICS = "mechanics"


class MedicalClass(str, PyEnum):
    CLASS_1 = "class_1"
    CLASS_2 = "class_2"
    CLASS_3 = "class_3"


class CrewMember(Base):
    __tablename__ = "crew_members"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Role & licensing
    role: Mapped[CrewRole] = mapped_column(
        Enum(CrewRole, name="crew_role", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    license_type: Mapped[LicenseType | None] = mapped_column(
        Enum(LicenseType, name="license_type", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    license_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    license_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Medical
    medical_class: Mapped[MedicalClass | None] = mapped_column(
        Enum(MedicalClass, name="medical_class", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    medical_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Passport & visas
    passport_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    passport_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    visa_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Employment
    date_of_hire: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[CrewStatus] = mapped_column(
        Enum(CrewStatus, name="crew_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=CrewStatus.ACTIVE,
        nullable=False,
    )
    base_airport: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Currency tracking (snapshot, updated on flight completion)
    last_90d_hours: Mapped[float | None] = mapped_column(Float, nullable=True, default=0)
    last_90d_landings: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    last_12m_hours: Mapped[float | None] = mapped_column(Float, nullable=True, default=0)
    last_flight_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_proficiency_date: Mapped[date | None] = mapped_column(Date, nullable=True)

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
    qualifications = relationship("CrewQualification", back_populates="crew", lazy="selectin", cascade="all, delete-orphan")

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<CrewMember {self.first_name} {self.last_name} ({self.role.value})>"


class QualificationType(str, PyEnum):
    TYPE_RATING = "type_rating"
    PROFICIENCY_CHECK = "proficiency_check"
    LINE_CHECK = "line_check"
    INSTRUMENT_RATING = "instrument_rating"
    RECURRENT_TRAINING = "recurrent_training"
    DIFFERENTIAL_TRAINING = "differential_training"
    HAZMAT = "hazmat"
    DGR = "dgr"
    FIRST_AID = "first_aid"


class QualificationStatus(str, PyEnum):
    CURRENT = "current"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"


class CrewQualification(Base):
    __tablename__ = "crew_qualifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    crew_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("crew_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    qual_type: Mapped[QualificationType] = mapped_column(
        Enum(QualificationType, name="qual_type", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[QualificationStatus] = mapped_column(
        Enum(QualificationStatus, name="qual_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=QualificationStatus.CURRENT,
        nullable=False,
    )
    aircraft_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="e.g. C208, PC12")
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    crew = relationship("CrewMember", back_populates="qualifications", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CrewQualification {self.qual_type.value} {'expired' if self.status == QualificationStatus.EXPIRED else 'current'}>"
