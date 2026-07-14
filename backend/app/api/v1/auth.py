"""
Authentication and user management endpoints.

Module 1 of the ParaRig Ops Suite — registration, login, tokens,
MFA setup/verification, and user invitations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_optional_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_invite_token,
    generate_mfa_secret,
    hash_password,
    verify_invite_token,
    verify_mfa_totp,
    verify_password,
)
from app.models.organization import Organization
from app.models.user import User
from app.schemas import (
    AcceptInviteRequest,
    InviteRequest,
    InviteResponse,
    LoginRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    MfaVerifyResponse,
    OrganizationResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Helpers ───────────────────────────────────────────────────────

def _create_tokens(user: User, org: Organization) -> dict[str, str]:
    """Create access + refresh tokens for a given user."""
    token_data = {
        "sub": user.id,
        "org_id": user.organization_id,
        "role": user.role,
        "email": user.email,
    }
    return {
        "access_token": create_access_token(data=token_data),
        "refresh_token": create_refresh_token(data=token_data),
    }


# ── Register ──────────────────────────────────────────────────────


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Create a new organization with the registering user as super_admin."""
    # Check slug availability
    existing = await db.execute(
        select(Organization).where(Organization.slug == body.org_slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already taken",
        )

    # Check email availability
    existing_user = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create organization
    org = Organization(
        id=str(uuid.uuid4()),
        name=body.org_name,
        slug=body.org_slug,
        timezone="America/Nassau",
        currency="USD",
        country="BS",
        regs=["FAR-135"],
        is_active=True,
        settings={},
    )
    db.add(org)
    await db.flush()

    # Create super_admin user
    user = User(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        phone=body.phone,
        role="super_admin",
        is_active=True,
        mfa_enabled=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await db.refresh(org)

    tokens = _create_tokens(user, org)

    return RegisterResponse(
        **tokens,
        organization=OrganizationResponse.model_validate(org),
        user=UserResponse.model_validate(user),
    )


# ── Login ─────────────────────────────────────────────────────────


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email + password, return JWT tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    db.add(user)

    # Fetch org for response
    org = await db.get(Organization, user.organization_id)

    await db.commit()

    tokens = _create_tokens(user, org)

    return TokenResponse(**tokens, user=UserResponse.model_validate(user))


# ── Refresh ───────────────────────────────────────────────────────


@router.post("/refresh")
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a refresh token for a new access + refresh token pair."""
    payload = decode_token(body.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    org = await db.get(Organization, user.organization_id)
    tokens = _create_tokens(user, org)

    return TokenResponse(**tokens, user=UserResponse.model_validate(user))


# ── Me ────────────────────────────────────────────────────────────


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


# ── MFA Setup ─────────────────────────────────────────────────────


@router.post("/mfa/setup")
async def mfa_setup(
    current_user: User = Depends(get_current_user),
) -> MfaSetupResponse:
    """Generate a new MFA secret for the current user."""
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA already enabled. Disable first to regenerate.",
        )

    secret, uri = generate_mfa_secret(current_user.email)
    # Store secret in user record (encrypted in production)
    current_user.mfa_secret = secret
    return MfaSetupResponse(secret=secret, uri=uri)


@router.post("/mfa/verify")
async def mfa_verify(
    body: MfaVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MfaVerifyResponse:
    """Verify a TOTP token and enable MFA."""
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not set up. Call /auth/mfa/setup first.",
        )

    if not verify_mfa_totp(current_user.mfa_secret, body.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA token",
        )

    current_user.mfa_enabled = True
    await db.commit()

    return MfaVerifyResponse(enabled=True)


# ── Invite ────────────────────────────────────────────────────────


@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: InviteRequest,
    current_user: User = Depends(get_current_user),
) -> InviteResponse:
    """Generate an invite token for a new user (ops_manager+ only)."""
    if current_user.role not in ("super_admin", "ops_manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admins and ops_managers can invite users",
        )

    token = generate_invite_token(
        email=body.email,
        org_id=current_user.organization_id,
        role=body.role,
    )

    return InviteResponse(invite_token=token, expires_in_hours=48)


@router.post("/accept-invite", status_code=status.HTTP_201_CREATED)
async def accept_invite(
    body: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Accept an invite token and create the user account."""
    payload = verify_invite_token(body.token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite token",
        )

    email = payload.get("email")
    org_id = payload.get("org_id")
    role = payload.get("role", "pilot")

    # Verify org still exists and is active
    org = await db.get(Organization, org_id)
    if not org or not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization not found or inactive",
        )

    user = User(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        phone=body.phone,
        role=role,
        is_active=True,
        mfa_enabled=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    tokens = _create_tokens(user, org)

    return TokenResponse(**tokens, user=UserResponse.model_validate(user))
