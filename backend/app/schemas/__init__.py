"""Pydantic schemas for authentication and user management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    org_name: str = Field(..., min_length=1, max_length=255)
    org_slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = None
    invite_code: Optional[str] = Field(None,
        description="Required for registration. Get one from your admin.")


class RegisterResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    organization: "OrganizationResponse"
    user: "UserResponse"


# ── MFA ───────────────────────────────────────────────────────────

class MfaSetupResponse(BaseModel):
    secret: str
    uri: str
    qr_b64: Optional[str] = None


class MfaVerifyRequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6)


class MfaVerifyResponse(BaseModel):
    enabled: bool
    backup_codes: Optional[list[str]] = None


class MfaChallengeRequest(BaseModel):
    temp_token: str
    totp_code: str


class MfaChallengeResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Invite ────────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(..., pattern=r"^(ops_manager|admin|pilot|mechanic|dispatcher|readonly)$")
    display_name: str = Field(..., min_length=1, max_length=255,
        description="Pre-set name so they don't have to enter it")
    phone: Optional[str] = None
    required_notes: Optional[str] = Field(None,
        description="E.g. 'Must provide emergency contact and date of birth'")


class InviteResponse(BaseModel):
    invite_token: str
    expires_in_hours: int = 48
    display_name: str
    email: str
    role: str
    required_notes: Optional[str] = None


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = None


# ── User ──────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    mfa_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


# ── Organization ──────────────────────────────────────────────────

class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: Optional[str] = None
    timezone: str
    currency: str
    country: str
    regs: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    regs: Optional[list[str]] = None
    settings: Optional[dict[str, Any]] = None
