"""User management endpoints — for super admin audit & permissions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.permissions import require_role
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
    last_login: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdatePermissionsBody(BaseModel):
    pii_clearance: bool | None = None
    is_active: bool | None = None
    role: str | None = None


@router.get("")
async def list_users(
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[UserPermissionsResponse]:
    """List all users in the org with their permissions."""
    result = await db.execute(
        select(User).where(
            User.organization_id == current_user.organization_id
        ).order_by(User.created_at.asc())
    )
    return [UserPermissionsResponse.model_validate(u) for u in result.scalars().all()]


@router.get("/{user_id}")
async def get_user_permissions(
    user_id: str,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> UserPermissionsResponse:
    """Get a single user's permissions."""
    user = await db.get(User, user_id)
    if not user or user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPermissionsResponse.model_validate(user)


@router.patch("/{user_id}/permissions")
async def update_user_permissions(
    user_id: str,
    body: UpdatePermissionsBody,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> UserPermissionsResponse:
    """Update a user's permissions (pii_clearance, is_active, role).

    Only SUPER_ADMIN can grant/revoke these. Changes are audit-logged.
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

    if "role" in update_data and update_data["role"] != target.role.value:
        old = target.role.value
        target.role = Role(update_data["role"])
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

    return UserPermissionsResponse.model_validate(target)
