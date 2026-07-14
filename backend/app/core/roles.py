"""Role enum shared across models, permissions, and auth.

Extracted to its own module to break circular imports between
app.models.user and app.core.permissions.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """Application roles ordered by privilege (highest first)."""

    SUPER_ADMIN = "super_admin"
    OPS_MANAGER = "ops_manager"
    ADMIN = "admin"
    PILOT = "pilot"
    MECHANIC = "mechanic"
    READONLY = "readonly"

    @classmethod
    def hierarchy(cls) -> dict[str, int]:
        """Return a mapping of role → privilege level (higher = more access)."""
        return {
            cls.SUPER_ADMIN: 100,
            cls.OPS_MANAGER: 80,
            cls.ADMIN: 60,
            cls.PILOT: 40,
            cls.MECHANIC: 40,
            cls.READONLY: 20,
        }

    def has_privilege(self, required: "Role") -> bool:
        """Check if this role has at least the privilege of *required*."""
        return self.hierarchy().get(self.value, 0) >= required.hierarchy().get(required.value, 0)
