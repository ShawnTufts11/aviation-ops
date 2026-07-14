"""Organization settings endpoints — session timeout, branding, etc."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_role
from app.core.roles import Role
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(prefix="/org", tags=["org"])


class OrgSettingsResponse(BaseModel):
    session_timeout_minutes: int = Field(default=480, ge=30, le=480)
    timezone: str = "America/Nassau"
    currency: str = "USD"
    country: str = "BS"

    model_config = {"from_attributes": True}


class UpdateOrgSettingsBody(BaseModel):
    session_timeout_minutes: int | None = Field(None, ge=30, le=480,
        description="Session timeout in minutes (30–480 / 8 hours max)")
    timezone: str | None = None
    currency: str | None = None
    country: str | None = None


@router.get("/settings")
async def get_org_settings(
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER, Role.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> OrgSettingsResponse:
    """Get current organization settings."""
    from sqlalchemy import select
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    settings = org.settings or {}
    return OrgSettingsResponse(
        session_timeout_minutes=settings.get("session_timeout_minutes", 480),
        timezone=org.timezone,
        currency=org.currency,
        country=org.country,
    )


@router.patch("/settings")
async def update_org_settings(
    body: UpdateOrgSettingsBody,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> OrgSettingsResponse:
    """Update organization settings. SUPER_ADMIN only."""
    from sqlalchemy import select
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Update JSON settings
    org_settings = org.settings or {}
    update_data = body.model_dump(exclude_unset=True)
    for key in ("session_timeout_minutes",):
        if key in update_data and update_data[key] is not None:
            org_settings[key] = update_data[key]

    # Update direct fields
    for key in ("timezone", "currency", "country"):
        if key in update_data and update_data[key] is not None:
            setattr(org, key, update_data[key])

    org.settings = org_settings
    db.add(org)
    await db.commit()

    return OrgSettingsResponse(
        session_timeout_minutes=org_settings.get("session_timeout_minutes", 480),
        timezone=org.timezone,
        currency=org.currency,
        country=org.country,
    )
