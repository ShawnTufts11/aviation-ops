"""SQLAlchemy ORM models — import all models here for Alembic auto-detection."""

from app.models.organization import Organization  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.aircraft import Aircraft, AircraftComponent  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.maintenance import MaintenanceTask  # noqa: F401
from app.models.flight import Flight, Route  # noqa: F401
from app.models.crew import CrewMember, CrewQualification  # noqa: F401
from app.models.document import Document  # noqa: F401

__all__ = [
    "Organization",
    "User",
    "Aircraft",
    "AircraftComponent",
    "AuditLog",
    "MaintenanceTask",
    "Flight",
    "Route",
]
