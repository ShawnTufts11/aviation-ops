"""User management endpoints — for admin audit & permissions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.features import Feature, get_effective_features
from app.core.permissions import require_feature, require_role
from app.core.roles import Role
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


class UserPermissionsResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    pii_clearance: bool
    feature_overrides: list[str] = []
    effective_features: list[str] = []
    permissions_version: int = 1
    last_login: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdatePermissionsBody(BaseModel):
    pii_clearance: bool | None = None
    is_active: bool | None = None
    role: str | None = None


@router.get("")
async def list_users(
    current_user: User = Depends(require_feature("admin:users")),
    db: AsyncSession = Depends(get_db),
) -> list[UserPermissionsResponse]:
    """List all users in the org with their permissions.

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


@router.get("/{user_id}")
async def get_user_permissions(
    user_id: str,
    current_user: User = Depends(require_feature("admin:users")),
    db: AsyncSession = Depends(get_db),
) -> UserPermissionsResponse:
    """Get a single user's permissions."""
    target = await db.get(User, user_id)
    if not target or target.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found")

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


@router.patch("/{user_id}/permissions")
async def update_user_permissions(
    user_id: str,
    body: UpdatePermissionsBody,
    current_user: User = Depends(require_feature("admin:users")),
    db: AsyncSession = Depends(get_db),
) -> UserPermissionsResponse:
    """Update a user's permissions (pii_clearance, is_active, role).

    Requires ``admin:users`` feature. Changes are audit-logged.
    """
    target = await db.get(User, user_id)
    if not target or target.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found")

    changes = []
    update_data = body.model_dump(exclude_unset=True)

    if "pii_clearance" in update_data and update_data["pii_clearance"] != target.pii_clearance:
        old = target.pii_clearance
        target.pii_clearance = update_data["pii_clearance"]
        changes.append(f"pii_clearance: {old} → {target.pii_clearance}")

    if "is_active" in update_data and update_data["is_active"] != target.is_active:
        old = target.is_active
        target.is_active = update_data["is_active"]
        changes.append(f"is_active: {old} → {target.is_active}")

    if "role" in update_data and update_data["role"] != (target.role.value if isinstance(target.role, Role) else target.role):
        old = target.role.value if isinstance(target.role, Role) else target.role
        target.role = Role(update_data["role"])
        target.permissions_version += 1  # Bump version on role change
        changes.append(f"role: {old} → {target.role.value}")

    db.add(target)
    await db.commit()
    await db.refresh(target)

    if changes:
        await log_action(
            db=db,
            org_id=current_user.organization_id,
            user_id=current_user.id,
            action="permissions.updated",
            entity_type="user",
            entity_id=target.id,
            new_values={"changes": changes},
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
