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
from app.core.features import Feature
from app.core.permissions import require_role
from app.core.roles import Role
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_invite_token,
    verify_invite_token,
    hash_password,
    verify_password,
    generate_mfa_secret,
    verify_mfa_totp,
)
from app.models.organization import Organization
from app.models.user import User
from app.schemas import (
    AcceptInviteRequest,
    InviteRequest,
    InviteResponse,
    LoginRequest,
    MfaChallengeRequest,
    MfaChallengeResponse,
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
    """Create access + refresh tokens for a given user.

    Reads session_timeout_minutes from the org's settings (capped at 480).
    """
    org_settings = org.settings or {}
    timeout = org_settings.get("session_timeout_minutes")
    token_data = {
        "sub": user.id,
        "org_id": user.organization_id,
        "org_slug": org.slug,
        "role": user.role,
        "email": user.email,
    }
    return {
        "access_token": create_access_token(data=token_data, timeout_minutes=timeout),
        "refresh_token": create_refresh_token(data=token_data),
    }


# ── Register ──────────────────────────────────────────────────────


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Register with an invite code. Creates a new organization (for client onboarding) or joins existing one.

    Supports:
    - Bootstrap code (creates root org)
    - Single-role invite codes
    - Multi-role invite codes (use ``selected_role`` to pick one)
    - Feature-scoped invite codes (extra features granted on accept)
    - Multi-use invite codes (track usage count)
    """
    from app.models.invite import InviteCode

    org_to_join: Organization | None = None
    is_bootstrap = body.invite_code == settings.INVITE_BOOTSTRAP_CODE

    if not body.invite_code and not is_bootstrap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invite code is required to register",
        )

    if not is_bootstrap:
        # Validate invite code
        result = await db.execute(
            select(InviteCode).where(
                InviteCode.code == body.invite_code,
                InviteCode.expires_at > datetime.now(timezone.utc),
            )
        )
        code = result.scalar_one_or_none()
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invite code",
            )

        # Check multi-use limits
        if code.max_uses > 0 and code.use_count >= code.max_uses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invite code has reached its maximum number of uses",
            )

        # Resolve role — either fixed role or chosen from allowed_roles
        resolved_role = code.role
        if code.allowed_roles:
            if body.selected_role:
                if body.selected_role not in code.allowed_roles:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid role. Invite allows: {code.allowed_roles}",
                    )
                resolved_role = body.selected_role
            else:
                # Default to first allowed role if not specified
                resolved_role = code.allowed_roles[0]

        # Determine granted features
        granted_features = list(code.granted_features or [])

        # If code has an org_id, user is joining an existing org
        if code.organization_id:
            org_to_join = await db.get(Organization, code.organization_id)
            if not org_to_join or not org_to_join.is_active:
                raise HTTPException(status_code=400, detail="Organization not found or inactive")

        # Mark usage — for multi-use codes, increment use_count
        code.use_count += 1
        if code.max_uses > 0 and code.use_count >= code.max_uses:
            code.is_used = True
        code.used_at = datetime.now(timezone.utc)
        db.add(code)
    else:
        resolved_role = "accountable_executive"
        granted_features = []

    # Check email
    existing_user = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    if org_to_join:
        # Joining existing org — create user with the resolved role and features
        user = User(
            id=str(uuid.uuid4()),
            organization_id=org_to_join.id,
            email=body.email,
            password_hash=hash_password(body.password),
            display_name=body.display_name,
            phone=body.phone,
            role=resolved_role,
            feature_overrides=granted_features,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        org = org_to_join
    else:
        # Creating new org (bootstrap or new-client invite code)
        existing = await db.execute(
            select(Organization).where(Organization.slug == body.org_slug)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Organization slug already taken",
            )

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

        user = User(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            email=body.email,
            password_hash=hash_password(body.password),
            display_name=body.display_name,
            phone=body.phone,
            role="accountable_executive",
            feature_overrides=[],
            is_active=True,
            mfa_enabled=False,
        )
        db.add(user)
        await db.flush()

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
):
    """Authenticate with email + password.

    If MFA is enabled for this user, returns a temp_token for
    the second factor step (/auth/mfa/challenge).
    """
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

    user.last_login = datetime.now(timezone.utc)
    db.add(user)
    org = await db.get(Organization, user.organization_id)
    await db.commit()

    # Audit log the login
    from app.core.audit import log_action
    await log_action(
        db=db, org_id=user.organization_id, user_id=user.id,
        action="login", entity_type="user", entity_id=user.id,
    )

    # If MFA is enabled, issue temp token instead of real tokens
    if user.mfa_enabled:
        temp_token = create_access_token(
            data={"sub": user.id, "org_id": user.organization_id, "role": user.role, "mfa_pending": True},
            expires_delta=timedelta(minutes=5),
        )
        return {"mfa_required": True, "temp_token": temp_token}

    tokens = _create_tokens(user, org)
    return TokenResponse(**tokens, user=UserResponse.model_validate(user))


@router.post("/mfa/challenge")
async def mfa_challenge(
    body: MfaChallengeRequest,
    db: AsyncSession = Depends(get_db),
) -> MfaChallengeResponse:
    """Verify TOTP code from an MFA challenge and issue real tokens."""
    payload = decode_token(body.temp_token)
    if payload is None or not payload.get("mfa_pending"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA challenge token",
        )

    user = await db.get(User, payload.get("sub"))
    if not user or not user.is_active or not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or MFA not configured",
        )

    if not verify_mfa_totp(user.mfa_secret, body.totp_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code",
        )

    org = await db.get(Organization, user.organization_id)
    tokens = _create_tokens(user, org)
    return MfaChallengeResponse(**tokens)


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
    db: AsyncSession = Depends(get_db),
) -> InviteResponse:
    """Invite a user — pre-creates their profile and generates invite link.

    Requires ``admin:users`` feature. Supports granted_features for
    permission overrides upon acceptance.

    The invited user sets their password when they accept.
    """
    # Check feature-level access instead of hardcoded role check
    from app.core.features import check_feature_access, Feature as Feat
    if not check_feature_access(current_user.role, Feat("admin:users"),
                                 {Feature(f) for f in (current_user.feature_overrides or [])}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to invite users",
        )

    # Check if user already exists
    from sqlalchemy import select
    from app.models.user import User as UserModel
    existing = await db.execute(
        select(UserModel).where(UserModel.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Validate granted_features
    for feat_str in body.granted_features:
        try:
            Feature(feat_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown feature: '{feat_str}'",
            )

    # Role constraint: can only invite <= own privilege
    inviter_priv = current_user.role.hierarchy().get(current_user.role.value, 0)
    requested_role_priv = Role(body.role).hierarchy().get(body.role, 0) if body.role else 0
    if requested_role_priv > inviter_priv:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot invite role '{body.role}' — it has higher privilege than your role",
        )

    # Pre-create the user profile (inactive until they accept)
    user = UserModel(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        email=body.email,
        display_name=body.display_name,
        phone=body.phone,
        role=body.role,
        password_hash="PENDING",  # placeholder, replaced on accept
        is_active=False,
        feature_overrides=body.granted_features,
    )
    db.add(user)
    await db.flush()

    token = generate_invite_token(
        email=body.email,
        org_id=current_user.organization_id,
        role=body.role,
        user_id=user.id,
        display_name=body.display_name,
    )

    await db.commit()

    return InviteResponse(
        invite_token=token,
        expires_in_hours=48,
        display_name=body.display_name,
        email=body.email,
        role=body.role,
        granted_features=body.granted_features,
        required_notes=body.required_notes,
    )


@router.post("/accept-invite", status_code=status.HTTP_201_CREATED)
async def accept_invite(
    body: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Accept an invite token and create the user account.

    Supports feature overrides pre-set on the user profile by the inviter.
    """
    payload = verify_invite_token(body.token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite token",
        )

    email = payload.get("email")
    user_id = payload.get("user_id")
    role = payload.get("role", "pilot")

    # Find the pre-created user profile
    from app.models.user import User as UserModel
    if user_id:
        user = await db.get(UserModel, user_id)
    else:
        # Fallback for legacy tokens without user_id
        result = await db.execute(
            select(UserModel).where(
                UserModel.email == email,
                UserModel.is_active == False,
            )
        )
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite not found or already accepted",
        )

    # Activate the user — preserve feature_overrides from the pre-created profile
    user.password_hash = hash_password(body.password)
    user.display_name = body.display_name or user.display_name
    if body.phone:
        user.phone = body.phone
    user.is_active = True
    db.add(user)
    await db.commit()
    await db.refresh(user)

    org = await db.get(Organization, user.organization_id)
    tokens = _create_tokens(user, org)

    return TokenResponse(**tokens, user=UserResponse.model_validate(user))
