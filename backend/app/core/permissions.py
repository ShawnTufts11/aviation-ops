"""
Role-Based Access Control (RBAC) dependencies for FastAPI.

Provides ``require_role`` dependency, ``require_org_membership``,
``require_feature``, ``require_pii_clearance``,
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
        async def admin_endpoint(user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS]))):
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


def require_feature(feature: str) -> Any:
    """Factory that returns a dependency checking the user's feature-level access.

    This is the granular counterpart of ``require_role`` — instead of checking
    which role the user has, it checks whether their role (plus any feature
    overrides on their profile) grants access to a specific feature.

    Usage::

        @router.get("/aircraft")
        async def list_aircraft(user: User = Depends(require_feature("aircraft:read"))):
            ...

    The feature string must match a :class:`app.core.features.Feature` enum value.
    """
    from app.core.features import Feature, check_feature_access

    # Validate feature at definition time
    feat = Feature(feature)

    async def _feature_checker(current_user: User = Depends(get_current_user)) -> User:
        overrides: set[Feature] | None = None
        if current_user.feature_overrides:
            overrides = {Feature(f) for f in current_user.feature_overrides if isinstance(f, str)}
            overrides |= {f for f in current_user.feature_overrides if isinstance(f, Feature)}

        if not check_feature_access(current_user.role, feat, overrides):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied — requires feature '{feat.value}'",
            )
        return current_user

    return _feature_checker


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


PII_CLEARANCE_ROLES = [Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS]


def require_pii_clearance() -> Any:
    """Restrict access to Personally Identifiable Information (PII).

    Requires the user to have pii_clearance=True on their profile,
    OR the ``pii:access`` feature override, OR be an Accountable Executive.
    """

    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == Role.ACCOUNTABLE_EXECUTIVE:
            return current_user
        if current_user.pii_clearance:
            return current_user
        # Check feature-level override
        if current_user.feature_overrides and "pii:access" in current_user.feature_overrides:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PII access requires pii_clearance on your user profile — contact your super admin",
        )

    return _checker


def has_pii_clearance(user: User) -> bool:
    """Check if a user has PII clearance without raising an error."""
    if user.role == Role.ACCOUNTABLE_EXECUTIVE:
        return True
    if user.pii_clearance:
        return True
    if user.feature_overrides and "pii:access" in user.feature_overrides:
        return True
    return False
