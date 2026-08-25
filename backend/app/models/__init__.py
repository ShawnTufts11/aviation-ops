"""SQLAlchemy ORM models — import all models here for Alembic auto-detection."""

from app.models.organization import Organization  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.aircraft import Aircraft, AircraftComponent  # noqa: F401
from app.models.airport import Airport  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.maintenance import MaintenanceTask  # noqa: F401
from app.models.flight import Flight, Route  # noqa: F401
from app.models.crew import CrewMember, CrewQualification  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.notification import Notification, EmergencyAlert  # noqa: F401
from app.models.finance import FinancialRecord  # noqa: F401
from app.models.leg_cost import LegCost  # noqa: F401
from app.models.mission import Mission, FlightLeg, ManifestEntry, AircraftFuelProfile  # noqa: F401
from app.models.passenger import Passenger  # noqa: F401
from app.models.invite import InviteCode  # noqa: F401
from app.models.logbook import PilotLogEntry  # noqa: F401
from app.models.flight_release import FlightRelease  # noqa: F401

__all__ = [
    "Organization",
    "User",
    "Aircraft",
    "AircraftComponent",
    "AuditLog",
    "MaintenanceTask",
    "Flight",
    "Route",
    "FlightRelease",
]
