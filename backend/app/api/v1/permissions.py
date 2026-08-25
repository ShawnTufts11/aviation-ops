"""
Permissions management endpoints for the personnel/permission system.

Provides:
- ``GET  /permissions/matrix``  — Full feature-per-role matrix
- ``GET  /permissions/me``      — Current user's effective features
- ``GET  /permissions/users``   — All users with their effective permissions
- ``GET  /permissions/users/{user_id}`` — Single user's permission details
- ``PATCH /permissions/users/{user_id}/features`` — Update user feature overrides
- ``POST /permissions/users/{user_id}/bump-version`` — Bump permissions_version
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.features import (
    FEATURE_PERMISSION_MATRIX,
    Feature,
    get_effective_features,
    get_role_features,
)
from app.core.permissions import require_feature, require_role
from app.core.roles import Role
from app.models.user import User
from app.schemas import (
    FeatureOverrideRequest,
    RoleFeatureMatrixResponse,
    UserPermissionsResponse,
)

router = APIRouter(prefix="/permissions", tags=["permissions"])


# ── Models ─────────────────────────────────────────────────────────────────


class FeaturesResponse(BaseModel):
    features: list[str]
    permissions_version: int


# ── Matrix / Discovery ─────────────────────────────────────────────────────


@router.get("/matrix")
async def get_permission_matrix(
    current_user: User = Depends(require_feature("admin:users")),
) -> RoleFeatureMatrixResponse:
    """Return the complete role-feature permission matrix.

    Requires ``admin:users`` feature access (Accountable Executive or
    Director of Operations by default).
    """
    matrix: dict[str, list[str]] = {}
    for role in Role:
        matrix[role.value] = sorted(f.value for f in get_role_features(role))

    return RoleFeatureMatrixResponse(
        roles=matrix,
        all_features=sorted(f.value for f in Feature),
    )


@router.get("/features")
async def list_all_features() -> list[dict[str, Any]]:
    """Return all known features grouped by category — publicly accessible."""
    categories = Feature.categories()
    return [
        {
            "category": cat,
            "features": [f.value for f in feats],
        }
        for cat, feats in categories.items()
    ]


# ── Self ───────────────────────────────────────────────────────────────────


@router.get("/me")
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
) -> FeaturesResponse:
    """Return the current user's effective feature set."""
    overrides: set[Feature] | None = None
    if current_user.feature_overrides:
        overrides = {Feature(f) for f in current_user.feature_overrides}

    effective = get_effective_features(current_user.role, overrides)
    return FeaturesResponse(
        features=sorted(f.value for f in effective),
        permissions_version=current_user.permissions_version,
    )


# ── User Permission Management ────────────────────────────────────────────


async def _get_org_user(
    user_id: str,
    current_user: User,
    db: AsyncSession,
) -> User:
    """Fetch a user within the same org or 404."""
    target = await db.get(User, user_id)
    if not target or target.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found")
    return target


@router.get("/users")
async def list_user_permissions(
    current_user: User = Depends(require_feature("admin:users")),
    db: AsyncSession = Depends(get_db),
) -> list[UserPermissionsResponse]:
    """List all users in the org with their effective permissions.

    Requires ``admin:users`` feature.
    """
    result = await db.execute(
        select(User).where(
            User.organization_id == current_user.organization_id
        ).order_by(User.created_at.asc())
    )
    users = result.scalars().all()

    responses = []
    for user in users:
        overrides: set[Feature] | None = None
        if user.feature_overrides:
            overrides = {Feature(f) for f in user.feature_overrides}
        effective = get_effective_features(user.role, overrides)
        responses.append(UserPermissionsResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role.value if isinstance(user.role, Role) else user.role,
            is_active=user.is_active,
            pii_clearance=user.pii_clearance,
            feature_overrides=list(user.feature_overrides or []),
            effective_features=sorted(f.value for f in effective),
            permissions_version=user.permissions_version,
            last_login=user.last_login,
            created_at=user.created_at,
        ))
    return responses


@router.get("/users/{user_id}")
async def get_user_permissions_detail(
    user_id: str,
    current_user: User = Depends(require_feature("admin:users")),
    db: AsyncSession = Depends(get_db),
) -> UserPermissionsResponse:
    """Get a single user's effective permissions.

    Requires ``admin:users`` feature.
    """
    target = await _get_org_user(user_id, current_user, db)
    overrides: set[Feature] | None = None
    if target.feature_overrides:
        overrides = {Feature(f) for f in target.feature_overrides}
    effective = get_effective_features(target.role, overrides)
    return UserPermissionsResponse(
        id=target.id,
        email=target.email,
        display_name=target.display_name,
        role=target.role.value if isinstance(target.role, Role) else target.role,
        is_active=target.is_active,
        pii_clearance=target.pii_clearance,
        feature_overrides=list(target.feature_overrides or []),
        effective_features=sorted(f.value for f in effective),
        permissions_version=target.permissions_version,
        last_login=target.last_login,
        created_at=target.created_at,
    )


@router.patch("/users/{user_id}/features")
async def update_user_feature_overrides(
    user_id: str,
    body: FeatureOverrideRequest,
    current_user: User = Depends(require_feature("admin:users")),
    db: AsyncSession = Depends(get_db),
) -> UserPermissionsResponse:
    """Update a user's feature overrides and bump permissions version.

    Only users with ``admin:users`` feature can manage overrides.
    Feature strings are validated against the ``Feature`` enum before applying.
    Changes are audit-logged.

    Pass an empty list to clear all overrides.
    """
    target = await _get_org_user(user_id, current_user, db)

    # Validate all feature strings
    valid_features: list[str] = []
    for feat_str in body.feature_overrides:
        try:
            Feature(feat_str)
            valid_features.append(feat_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown feature: '{feat_str}'. See GET /permissions/features for valid features.",
            )

    old_overrides = list(target.feature_overrides or [])
    target.feature_overrides = valid_features
    target.permissions_version += 1
    db.add(target)
    await db.commit()
    await db.refresh(target)

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    await log_action(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        action="permissions.feature_overrides_updated",
        entity_type="user",
        entity_id=target.id,
        old_values={"feature_overrides": old_overrides},
        new_values={"feature_overrides": valid_features, "permissions_version": target.permissions_version},
    )

    overrides: set[Feature] | None = None
    if target.feature_overrides:
        overrides = {Feature(f) for f in target.feature_overrides}
    effective = get_effective_features(target.role, overrides)
    return UserPermissionsResponse(
        id=target.id,
        email=target.email,
        display_name=target.display_name,
        role=target.role.value if isinstance(target.role, Role) else target.role,
        is_active=target.is_active,
        pii_clearance=target.pii_clearance,
        feature_overrides=list(target.feature_overrides or []),
        effective_features=sorted(f.value for f in effective),
        permissions_version=target.permissions_version,
        last_login=target.last_login,
        created_at=target.created_at,
    )


@router.post("/users/{user_id}/bump-version")
async def bump_permissions_version(
    user_id: str,
    current_user: User = Depends(require_feature("admin:users")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Bump a user's permissions version to force frontend cache refresh."""
    target = await _get_org_user(user_id, current_user, db)
    target.permissions_version += 1
    db.add(target)
    await db.commit()

    return {
        "detail": "Permissions version bumped",
        "user_id": target.id,
        "permissions_version": target.permissions_version,
    }
