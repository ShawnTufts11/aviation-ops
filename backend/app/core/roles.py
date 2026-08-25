"""Role enum shared across models, permissions, and auth.

Extracted to its own module to break circular imports between
app.models.user and app.core.permissions.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """FAA Part 135 operational roles ordered by privilege (highest first).

    Permission Matrix (✅ = can access, ❌ = cannot access):
    ┌─────────────────────────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
    │ Resource                │  AE  │  DoO │  DoS │  CP  │  DoM │  VPF │  Ops │  Dsp │  Plt │  MxT │  Vwr │
    ├─────────────────────────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
    │ Aircraft: Read          │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │
    │ Aircraft: Write         │  ✅  │  ✅  │  ❌  │  ✅  │  ✅  │  ❌  │  ✅  │  ❌  │  ❌  │  ❌  │  ❌  │
    │ Aircraft: Delete        │  ✅  │  ✅  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │
    │ Flights: Read           │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ❌  │  ✅  │
    │ Flights: Create         │  ✅  │  ✅  │  ❌  │  ✅  │  ❌  │  ❌  │  ✅  │  ✅  │  ❌  │  ❌  │  ❌  │
    │ Maintenance: Read       │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │
    │ Maintenance: Write      │  ✅  │  ✅  │  ❌  │  ✅  │  ✅  │  ❌  │  ✅  │  ❌  │  ❌  │  ✅  │  ❌  │
    │ Crew: Read              │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ❌  │  ✅  │
    │ Crew: Write             │  ✅  │  ✅  │  ❌  │  ✅  │  ❌  │  ❌  │  ✅  │  ❌  │  ❌  │  ❌  │  ❌  │
    │ Compliance: Read        │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ❌  │  ❌  │  ✅  │
    │ Compliance: Write       │  ✅  │  ✅  │  ✅  │  ❌  │  ❌  │  ❌  │  ✅  │  ❌  │  ❌  │  ❌  │  ❌  │
    │ Finance: Read           │  ✅  │  ✅  │  ✅  │  ❌  │  ❌  │  ✅  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │
    │ Finance: Write          │  ✅  │  ✅  │  ❌  │  ❌  │  ❌  │  ✅  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │
    │ Admin: Users            │  ✅  │  ✅  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │
    │ Admin: Settings         │  ✅  │  ✅  │  ✅  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │  ❌  │
    │ Safety: Read            │  ✅  │  ✅  │  ✅  │  ✅  │  ✅  │  ❌  │  ✅  │  ❌  │  ❌  │  ❌  │  ❌  │
    │ Safety: Write           │  ✅  │  ✅  │  ✅  │  ❌  │  ❌  │  ❌  │  ✅  │  ❌  │  ❌  │  ❌  │  ❌  │
    └─────────────────────────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘

    Legend:
      AE  = Accountable Executive (CEO)
      DoO = Director of Operations
      DoS = Director of Safety
      CP  = Chief Pilot
      DoM = Director of Maintenance
      VPF = VP Finance
      Ops = Ops Manager
      Dsp = Dispatcher
      Plt = Pilot
      MxT = Maintenance Technician
      Vwr = Viewer
    """

    ACCOUNTABLE_EXECUTIVE = "accountable_executive"
    DIRECTOR_OF_OPERATIONS = "director_of_operations"
    DIRECTOR_OF_SAFETY = "director_of_safety"
    CHIEF_PILOT = "chief_pilot"
    DIRECTOR_OF_MAINTENANCE = "director_of_maintenance"
    VP_FINANCE = "vp_finance"
    OPS_MANAGER = "ops_manager"
    DISPATCHER = "dispatcher"
    PILOT = "pilot"
    MAINTENANCE_TECHNICIAN = "maintenance_technician"
    VIEWER = "viewer"

    @classmethod
    def hierarchy(cls) -> dict[str, int]:
        """Return a mapping of role → privilege level (higher = more access)."""
        return {
            cls.ACCOUNTABLE_EXECUTIVE: 100,
            cls.DIRECTOR_OF_OPERATIONS: 95,
            cls.DIRECTOR_OF_SAFETY: 90,
            cls.CHIEF_PILOT: 85,
            cls.DIRECTOR_OF_MAINTENANCE: 80,
            cls.VP_FINANCE: 75,
            cls.OPS_MANAGER: 70,
            cls.DISPATCHER: 50,
            cls.PILOT: 40,
            cls.MAINTENANCE_TECHNICIAN: 35,
            cls.VIEWER: 20,
        }

    def has_privilege(self, required: "Role") -> bool:
        """Check if this role has at least the privilege of *required*."""
        return self.hierarchy().get(self.value, 0) >= required.hierarchy().get(required.value, 0)

    # ── Feature-level access (lazy-imported to avoid circular deps) ──────

    def has_feature(self, feature: str) -> bool:
        """Check if this role can access a given feature.

        Wraps :func:`app.core.features.check_feature_access` for convenience.
        Feature can be a string or a ``Feature`` enum value.
        """
        from app.core.features import Feature, check_feature_access

        feat = Feature(feature) if isinstance(feature, str) else feature
        return check_feature_access(self, feat)

    def get_features(self) -> list[str]:
        """Return the list of feature strings this role can access."""
        from app.core.features import get_role_features

        return sorted(f.value for f in get_role_features(self))

    @classmethod
    def all_features(cls) -> list[str]:
        """Return all known features across all roles."""
        from app.core.features import Feature

        return sorted(f.value for f in Feature)
