"""
Role-Based Access Control (RBAC) dependencies for FastAPI.

Provides ``require_role`` dependency, ``require_org_membership``,
and ``get_current_user`` for extracting the authenticated user from JWT.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.roles import Role
from app.core.security import decode_token
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


# ── Dependencies ───────────────────────────────────────────────────────────


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the Bearer JWT.

    Raises 401 if the token is missing, invalid, or the user does not exist.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Same as *get_current_user* but returns *None* instead of raising 401."""
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials)
    if payload is None:
        return None

    user_id: str | None = payload.get("sub")
    if user_id is None:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def require_role(required_roles: list[Role]) -> Any:
    """Factory that returns a dependency checking the user's role.

    Usage::

        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role([Role.ADMIN, Role.SUPER_ADMIN]))):
            ...
    """

    async def _role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in required_roles]}",
            )
        return current_user

    return _role_checker


async def require_org_membership(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify the user belongs to an organization (non-null organization_id)."""
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any organization",
        )
    return current_user


# ── PII Access Control ─────────────────────────────────────────


PII_CLEARANCE_ROLES = [Role.SUPER_ADMIN, Role.OPS_MANAGER]


def require_pii_clearance() -> Any:
    """Restrict access to Personally Identifiable Information (PII).

    Only SUPER_ADMIN and OPS_MANAGER roles can view full passenger
    profiles (passport numbers, DOB, SSN, etc.). Other roles get
    redacted/minimal data.

    Usage:
        user: User = Depends(require_pii_clearance()),
    """

    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in PII_CLEARANCE_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="PII access requires SUPER_ADMIN or OPS_MANAGER role",
            )
        return current_user

    return _checker


def has_pii_clearance(user: User) -> bool:
    """Check if a user has PII clearance without raising an error."""
    return user.role in PII_CLEARANCE_ROLES
