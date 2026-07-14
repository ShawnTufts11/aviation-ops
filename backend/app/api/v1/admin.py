"""Admin endpoints: create client orgs, generate invite codes, system setup."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.config import settings
from app.core.permissions import require_role
from app.core.roles import Role
from app.core.security import hash_password
from app.models.invite import InviteCode
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateOrgRequest(BaseModel):
    org_name: str = Field(..., min_length=1, max_length=255)
    org_slug: str = Field(..., min_length=2, max_length=100,
        description="URL-safe slug (e.g. 'client-name')")
    admin_email: str = Field(..., min_length=5)
    admin_name: str = Field(..., min_length=1, max_length=255)
    admin_role: str = "admin"
    timezone: str = "America/Nassau"
    currency: str = "USD"
    country: str = "BS"


class CreateOrgResponse(BaseModel):
    organization_id: str
    organization_name: str
    admin_user_id: str
    admin_email: str
    invite_code: str
    invite_expires: str


class GenerateInviteCodeRequest(BaseModel):
    organization_id: str | None = None
    role: str = "admin"
    description: str | None = None
    expires_in_days: int = 30


class InviteCodeResponse(BaseModel):
    code: str
    organization_id: str | None
    role: str
    expires_at: str
    description: str | None


class BootstrapCheckResponse(BaseModel):
    bootstrap_used: bool
    registration_enabled: bool
    bootstrap_code: str | None


@router.get("/bootstrap-status")
async def bootstrap_status(
    db: AsyncSession = Depends(get_db),
) -> BootstrapCheckResponse:
    """Check if the bootstrap code has been used. Public — no auth needed."""
    result = await db.execute(
        select(InviteCode).where(
            InviteCode.code == settings.INVITE_BOOTSTRAP_CODE
        )
    )
    code = result.scalar_one_or_none()
    return BootstrapCheckResponse(
        bootstrap_used=code.is_used if code else False,
        registration_enabled=False,
        bootstrap_code=settings.INVITE_BOOTSTRAP_CODE if not (code and code.is_used) else None,
    )


@router.post("/create-org", status_code=status.HTTP_201_CREATED)
async def create_client_organization(
    body: CreateOrgRequest,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> CreateOrgResponse:
    """Create a new client organization with an initial admin user + invite code.

    SUPER_ADMIN only. This is how you onboard new clients.
    """
    # Check slug
    existing = await db.execute(
        select(Organization).where(Organization.slug == body.org_slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Organization slug already taken")

    # Check email
    existing_user = await db.execute(
        select(User).where(User.email == body.admin_email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create org
    org = Organization(
        id=str(uuid.uuid4()),
        name=body.org_name,
        slug=body.org_slug,
        timezone=body.timezone,
        currency=body.currency,
        country=body.country,
        regs=["FAR-135"],
        is_active=True,
        settings={},
    )
    db.add(org)
    await db.flush()

    # Create admin user (inactive — must accept invite)
    admin_user = User(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        email=body.admin_email,
        display_name=body.admin_name,
        role=body.admin_role,
        password_hash="PENDING",
        is_active=False,
    )
    db.add(admin_user)
    await db.flush()

    # Generate invite code
    code_str = f"{body.org_slug.upper()}-{uuid.uuid4().hex[:6].upper()}"
    expires = datetime.now(timezone.utc) + timedelta(days=60)
    invite_code = InviteCode(
        id=str(uuid.uuid4()),
        code=code_str,
        organization_id=org.id,
        role=body.admin_role,
        description=f"Onboarding invite for {body.org_name}",
        is_used=False,
        expires_at=expires,
        created_by=current_user.id,
    )
    db.add(invite_code)
    await db.commit()

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="admin.create_org", entity_type="organization",
        entity_id=org.id,
        new_values={"org_name": body.org_name, "admin_email": body.admin_email},
    )

    return CreateOrgResponse(
        organization_id=org.id,
        organization_name=body.org_name,
        admin_user_id=admin_user.id,
        admin_email=body.admin_email,
        invite_code=code_str,
        invite_expires=expires.isoformat(),
    )


@router.post("/invite-codes")
async def generate_invite_code(
    body: GenerateInviteCodeRequest,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> InviteCodeResponse:
    """Generate a reusable invite code for an existing org."""
    org_id = body.organization_id or current_user.organization_id

    code_str = f"INV-{uuid.uuid4().hex[:8].upper()}"
    expires = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
    invite = InviteCode(
        id=str(uuid.uuid4()),
        code=code_str,
        organization_id=org_id,
        role=body.role,
        description=body.description,
        expires_at=expires,
        created_by=current_user.id,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    return InviteCodeResponse(
        code=code_str,
        organization_id=org_id,
        role=body.role,
        expires_at=expires.isoformat(),
        description=body.description,
    )


@router.get("/invite-codes")
async def list_invite_codes(
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all invite codes for audit purposes."""
    result = await db.execute(
        select(InviteCode).order_by(InviteCode.created_at.desc()).limit(100)
    )
    return [
        {
            "code": c.code,
            "organization_id": c.organization_id,
            "role": c.role,
            "is_used": c.is_used,
            "used_by": c.used_by,
            "expires_at": c.expires_at.isoformat(),
            "description": c.description,
            "created_at": c.created_at.isoformat(),
        }
        for c in result.scalars().all()
    ]
