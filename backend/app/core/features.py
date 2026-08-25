"""
Feature-level permission system for role-based access control.

Each ``Feature`` represents a discrete capability (e.g. ``AIRCRAFT_READ``).
The :data:`FEATURE_PERMISSION_MATRIX` maps each role to the set of features
it is allowed to access — this is the code-level enforcement of the permission
matrix documented in :mod:`app.core.roles`.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class Feature(str, Enum):
    """Granular features that can be enabled/disabled per role."""

    # ── Aircraft ──────────────────────────────────────────────────────────
    AIRCRAFT_READ = "aircraft:read"
    AIRCRAFT_WRITE = "aircraft:write"
    AIRCRAFT_DELETE = "aircraft:delete"

    # ── Flights ───────────────────────────────────────────────────────────
    FLIGHTS_READ = "flights:read"
    FLIGHTS_CREATE = "flights:create"

    # ── Maintenance ───────────────────────────────────────────────────────
    MAINTENANCE_READ = "maintenance:read"
    MAINTENANCE_WRITE = "maintenance:write"

    # ── Crew ──────────────────────────────────────────────────────────────
    CREW_READ = "crew:read"
    CREW_WRITE = "crew:write"

    # ── Compliance ────────────────────────────────────────────────────────
    COMPLIANCE_READ = "compliance:read"
    COMPLIANCE_WRITE = "compliance:write"

    # ── Finance ───────────────────────────────────────────────────────────
    FINANCE_READ = "finance:read"
    FINANCE_WRITE = "finance:write"

    # ── Admin ─────────────────────────────────────────────────────────────
    ADMIN_USERS = "admin:users"
    ADMIN_SETTINGS = "admin:settings"

    # ── Safety ────────────────────────────────────────────────────────────
    SAFETY_READ = "safety:read"
    SAFETY_WRITE = "safety:write"

    # ── Routes / Mission Planning ─────────────────────────────────────────
    ROUTES_PLAN = "routes:plan"
    ROUTES_VIEW = "routes:view"

    # ── Passenger / PII ───────────────────────────────────────────────────
    PASSENGERS_READ = "passengers:read"
    PASSENGERS_WRITE = "passengers:write"
    PII_ACCESS = "pii:access"

    # ── Reports & Exports ─────────────────────────────────────────────────
    REPORTS_VIEW = "reports:view"
    EXPORT_DATA = "export:data"

    # ── Notifications / Comms ─────────────────────────────────────────────
    COMMS_SEND = "comms:send"
    COMMS_VIEW = "comms:view"

    @classmethod
    def categories(cls) -> dict[str, list[Feature]]:
        """Return features grouped by domain category."""
        return {
            "aircraft": [cls.AIRCRAFT_READ, cls.AIRCRAFT_WRITE, cls.AIRCRAFT_DELETE],
            "flights": [cls.FLIGHTS_READ, cls.FLIGHTS_CREATE],
            "maintenance": [cls.MAINTENANCE_READ, cls.MAINTENANCE_WRITE],
            "crew": [cls.CREW_READ, cls.CREW_WRITE],
            "compliance": [cls.COMPLIANCE_READ, cls.COMPLIANCE_WRITE],
            "finance": [cls.FINANCE_READ, cls.FINANCE_WRITE],
            "admin": [cls.ADMIN_USERS, cls.ADMIN_SETTINGS],
            "safety": [cls.SAFETY_READ, cls.SAFETY_WRITE],
            "routes": [cls.ROUTES_PLAN, cls.ROUTES_VIEW],
            "passengers": [cls.PASSENGERS_READ, cls.PASSENGERS_WRITE, cls.PII_ACCESS],
            "reports": [cls.REPORTS_VIEW, cls.EXPORT_DATA],
            "comms": [cls.COMMS_SEND, cls.COMMS_VIEW],
        }


# ── Permission Matrix ──────────────────────────────────────────────────────
# Maps each Role → set of Feature values they are allowed to access.
# This is the code-level enforcement of the matrix documented in app.core.roles.
#
# Import Role lazily to avoid circular imports at module level.
# The matrix is resolved at call time in has_feature() and require_feature().

from app.core.roles import Role  # noqa: E402


FEATURE_PERMISSION_MATRIX: Final[dict[Role, set[Feature]]] = {
    # ── Accountable Executive (CEO) — full access ─────────────────────────
    Role.ACCOUNTABLE_EXECUTIVE: {
        Feature.AIRCRAFT_READ, Feature.AIRCRAFT_WRITE, Feature.AIRCRAFT_DELETE,
        Feature.FLIGHTS_READ, Feature.FLIGHTS_CREATE,
        Feature.MAINTENANCE_READ, Feature.MAINTENANCE_WRITE,
        Feature.CREW_READ, Feature.CREW_WRITE,
        Feature.COMPLIANCE_READ, Feature.COMPLIANCE_WRITE,
        Feature.FINANCE_READ, Feature.FINANCE_WRITE,
        Feature.ADMIN_USERS, Feature.ADMIN_SETTINGS,
        Feature.SAFETY_READ, Feature.SAFETY_WRITE,
        Feature.ROUTES_PLAN, Feature.ROUTES_VIEW,
        Feature.PASSENGERS_READ, Feature.PASSENGERS_WRITE, Feature.PII_ACCESS,
        Feature.REPORTS_VIEW, Feature.EXPORT_DATA,
        Feature.COMMS_SEND, Feature.COMMS_VIEW,
    },

    # ── Director of Operations ────────────────────────────────────────────
    Role.DIRECTOR_OF_OPERATIONS: {
        Feature.AIRCRAFT_READ, Feature.AIRCRAFT_WRITE, Feature.AIRCRAFT_DELETE,
        Feature.FLIGHTS_READ, Feature.FLIGHTS_CREATE,
        Feature.MAINTENANCE_READ, Feature.MAINTENANCE_WRITE,
        Feature.CREW_READ, Feature.CREW_WRITE,
        Feature.COMPLIANCE_READ, Feature.COMPLIANCE_WRITE,
        Feature.FINANCE_READ, Feature.FINANCE_WRITE,
        Feature.ADMIN_USERS, Feature.ADMIN_SETTINGS,
        Feature.SAFETY_READ, Feature.SAFETY_WRITE,
        Feature.ROUTES_PLAN, Feature.ROUTES_VIEW,
        Feature.PASSENGERS_READ, Feature.PASSENGERS_WRITE, Feature.PII_ACCESS,
        Feature.REPORTS_VIEW, Feature.EXPORT_DATA,
        Feature.COMMS_SEND, Feature.COMMS_VIEW,
    },

    # ── Director of Safety ────────────────────────────────────────────────
    Role.DIRECTOR_OF_SAFETY: {
        Feature.AIRCRAFT_READ, Feature.FLIGHTS_READ,
        Feature.MAINTENANCE_READ,
        Feature.CREW_READ,
        Feature.COMPLIANCE_READ, Feature.COMPLIANCE_WRITE,
        Feature.FINANCE_READ,
        Feature.ADMIN_SETTINGS,
        Feature.SAFETY_READ, Feature.SAFETY_WRITE,
        Feature.ROUTES_VIEW,
        Feature.PASSENGERS_READ,
        Feature.REPORTS_VIEW, Feature.EXPORT_DATA,
        Feature.COMMS_VIEW,
    },

    # ── Chief Pilot ───────────────────────────────────────────────────────
    Role.CHIEF_PILOT: {
        Feature.AIRCRAFT_READ, Feature.AIRCRAFT_WRITE,
        Feature.FLIGHTS_READ, Feature.FLIGHTS_CREATE,
        Feature.MAINTENANCE_READ, Feature.MAINTENANCE_WRITE,
        Feature.CREW_READ, Feature.CREW_WRITE,
        Feature.COMPLIANCE_READ,
        Feature.SAFETY_READ,
        Feature.ROUTES_PLAN, Feature.ROUTES_VIEW,
        Feature.PASSENGERS_READ,
        Feature.REPORTS_VIEW,
        Feature.COMMS_SEND, Feature.COMMS_VIEW,
    },

    # ── Director of Maintenance ───────────────────────────────────────────
    Role.DIRECTOR_OF_MAINTENANCE: {
        Feature.AIRCRAFT_READ, Feature.AIRCRAFT_WRITE,
        Feature.FLIGHTS_READ,
        Feature.MAINTENANCE_READ, Feature.MAINTENANCE_WRITE,
        Feature.CREW_READ,
        Feature.COMPLIANCE_READ,
        Feature.SAFETY_READ,
        Feature.ROUTES_VIEW,
        Feature.PASSENGERS_READ,
        Feature.REPORTS_VIEW,
        Feature.COMMS_VIEW,
    },

    # ── VP Finance ────────────────────────────────────────────────────────
    Role.VP_FINANCE: {
        Feature.AIRCRAFT_READ,
        Feature.FLIGHTS_READ,
        Feature.MAINTENANCE_READ,
        Feature.CREW_READ,
        Feature.COMPLIANCE_READ,
        Feature.FINANCE_READ, Feature.FINANCE_WRITE,
        Feature.REPORTS_VIEW, Feature.EXPORT_DATA,
        Feature.COMMS_VIEW,
    },

    # ── Ops Manager ──────────────────────────────────────────────────────
    Role.OPS_MANAGER: {
        Feature.AIRCRAFT_READ, Feature.AIRCRAFT_WRITE,
        Feature.FLIGHTS_READ, Feature.FLIGHTS_CREATE,
        Feature.MAINTENANCE_READ, Feature.MAINTENANCE_WRITE,
        Feature.CREW_READ, Feature.CREW_WRITE,
        Feature.COMPLIANCE_READ, Feature.COMPLIANCE_WRITE,
        Feature.SAFETY_READ, Feature.SAFETY_WRITE,
        Feature.ROUTES_PLAN, Feature.ROUTES_VIEW,
        Feature.PASSENGERS_READ,
        Feature.REPORTS_VIEW,
        Feature.COMMS_SEND, Feature.COMMS_VIEW,
    },

    # ── Dispatcher ────────────────────────────────────────────────────────
    Role.DISPATCHER: {
        Feature.AIRCRAFT_READ,
        Feature.FLIGHTS_READ, Feature.FLIGHTS_CREATE,
        Feature.MAINTENANCE_READ,
        Feature.CREW_READ,
        Feature.COMPLIANCE_READ,
        Feature.ROUTES_PLAN, Feature.ROUTES_VIEW,
        Feature.PASSENGERS_READ,
        Feature.COMMS_SEND, Feature.COMMS_VIEW,
    },

    # ── Pilot ─────────────────────────────────────────────────────────────
    Role.PILOT: {
        Feature.AIRCRAFT_READ,
        Feature.FLIGHTS_READ,
        Feature.MAINTENANCE_READ,
        Feature.CREW_READ,
        Feature.ROUTES_PLAN, Feature.ROUTES_VIEW,
        Feature.PASSENGERS_READ,
        Feature.COMMS_SEND, Feature.COMMS_VIEW,
    },

    # ── Maintenance Technician ────────────────────────────────────────────
    Role.MAINTENANCE_TECHNICIAN: {
        Feature.AIRCRAFT_READ,
        Feature.MAINTENANCE_READ, Feature.MAINTENANCE_WRITE,
        Feature.CREW_READ,
        Feature.ROUTES_VIEW,
        Feature.COMMS_VIEW,
    },

    # ── Viewer (read-only) ────────────────────────────────────────────────
    Role.VIEWER: {
        Feature.AIRCRAFT_READ,
        Feature.FLIGHTS_READ,
        Feature.MAINTENANCE_READ,
        Feature.CREW_READ,
        Feature.COMPLIANCE_READ,
        Feature.ROUTES_VIEW,
        Feature.PASSENGERS_READ,
        Feature.COMMS_VIEW,
        Feature.REPORTS_VIEW,
    },
}


# ── Resolver ───────────────────────────────────────────────────────────────


def get_role_features(role: Role) -> set[Feature]:
    """Return the set of features a given role is allowed to access.

    Falls back to ``{VIEWER}``-level features if the role isn't found
    in the matrix (defensive fallback).
    """
    return FEATURE_PERMISSION_MATRIX.get(role, FEATURE_PERMISSION_MATRIX[Role.VIEWER])


def check_feature_access(role: Role, feature: Feature, feature_overrides: set[Feature] | None = None) -> bool:
    """Check whether *role* can access *feature*, considering any overrides.

    Args:
        role: The user's role.
        feature: The feature to check.
        feature_overrides: Optional set of feature overrides on the user record.
            If provided and the feature is in this set, access is granted
            regardless of role.

    Returns:
        True if access is allowed.
    """
    # Overrides take precedence
    if feature_overrides and feature in feature_overrides:
        return True

    return feature in get_role_features(role)


def get_effective_features(role: Role, feature_overrides: set[Feature] | None = None) -> set[Feature]:
    """Return the full set of features available to a role, including overrides."""
    base = get_role_features(role).copy()
    if feature_overrides:
        base |= feature_overrides
    return base
