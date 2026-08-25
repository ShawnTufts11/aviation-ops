"""Tests for Module 1: Authentication, Registration, MFA, and RBAC."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, decode_token


# ── Registration ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_creates_org_and_user(client: AsyncClient):
    """Register a new org + super_admin user."""
    payload = {
        "org_name": "New Charter Co",
        "org_slug": "new-charter-co",
        "email": "ceo@newcharter.aero",
        "password": "StrongPass1!",
        "display_name": "CEO",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["organization"]["name"] == "New Charter Co"
    assert data["organization"]["slug"] == "new-charter-co"
    assert data["user"]["email"] == "ceo@newcharter.aero"
    assert data["user"]["role"] == "super_admin"
    assert data["access_token"] is not None
    assert data["refresh_token"] is not None


@pytest.mark.asyncio
async def test_register_duplicate_slug(client: AsyncClient):
    """Reject duplicate org slugs."""
    payload = {
        "org_name": "First Org",
        "org_slug": "first-org",
        "email": "a@test.com",
        "password": "StrongPass1!",
        "display_name": "A",
    }
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Reject duplicate emails."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Org One",
            "org_slug": "org-one",
            "email": "dup@test.com",
            "password": "StrongPass1!",
            "display_name": "Dup",
        },
    )
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Org Two",
            "org_slug": "org-two",
            "email": "dup@test.com",
            "password": "StrongPass1!",
            "display_name": "Dup",
        },
    )
    assert resp.status_code == 409


# ── Login ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Login with valid credentials returns tokens."""
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Login Test",
            "org_slug": "login-test",
            "email": "user@logintest.com",
            "password": "StrongPass1!",
            "display_name": "User",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@logintest.com", "password": "StrongPass1!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["email"] == "user@logintest.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Login with wrong password returns 401."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Bad Pass",
            "org_slug": "bad-pass",
            "email": "bad@test.com",
            "password": "StrongPass1!",
            "display_name": "Bad",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "bad@test.com", "password": "WrongPass123!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Login for nonexistent email returns 401."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@void.com", "password": "DoesntMatter1!"},
    )
    assert resp.status_code == 401


# ── Token verification ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_me_with_token(client: AsyncClient):
    """GET /auth/me returns the user profile when authenticated."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Me Test",
            "org_slug": "me-test",
            "email": "me@test.com",
            "password": "StrongPass1!",
            "display_name": "Me",
        },
    )
    token = reg_resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"
    assert resp.json()["display_name"] == "Me"
    assert resp.json()["role"] == "super_admin"


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    """GET /auth/me without token returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_bad_token(client: AsyncClient):
    """GET /auth/me with invalid token returns 401."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalidtoken123"},
    )
    assert resp.status_code == 401


# ── Token refresh ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """Refresh endpoint returns new access token."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Refresh Test",
            "org_slug": "refresh-test",
            "email": "refresh@test.com",
            "password": "StrongPass1!",
            "display_name": "Ref",
        },
    )
    refresh = reg.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "refresh@test.com"


# ── RBAC ─────────────────────────────────────────────────────────


def test_role_hierarchy():
    """Verify role privilege hierarchy is correct."""
    from app.core.roles import Role

    hierarchy = Role.hierarchy()
    # ── FAA Part 135 hierarchy ──────────────────────────────
    assert hierarchy[Role.ACCOUNTABLE_EXECUTIVE] > hierarchy[Role.DIRECTOR_OF_OPERATIONS]
    assert hierarchy[Role.DIRECTOR_OF_OPERATIONS] > hierarchy[Role.DIRECTOR_OF_SAFETY]
    assert hierarchy[Role.DIRECTOR_OF_SAFETY] > hierarchy[Role.CHIEF_PILOT]
    assert hierarchy[Role.CHIEF_PILOT] > hierarchy[Role.DIRECTOR_OF_MAINTENANCE]
    assert hierarchy[Role.DIRECTOR_OF_MAINTENANCE] > hierarchy[Role.VP_FINANCE]
    assert hierarchy[Role.VP_FINANCE] > hierarchy[Role.OPS_MANAGER]
    assert hierarchy[Role.OPS_MANAGER] > hierarchy[Role.DISPATCHER]
    assert hierarchy[Role.DISPATCHER] > hierarchy[Role.PILOT]
    assert hierarchy[Role.PILOT] > hierarchy[Role.MAINTENANCE_TECHNICIAN]
    assert hierarchy[Role.MAINTENANCE_TECHNICIAN] > hierarchy[Role.VIEWER]


def test_role_privilege_check():
    """Verify has_privilege works correctly."""
    from app.core.roles import Role

    assert Role.ACCOUNTABLE_EXECUTIVE.has_privilege(Role.VIEWER)
    assert Role.DIRECTOR_OF_OPERATIONS.has_privilege(Role.PILOT)
    assert not Role.PILOT.has_privilege(Role.OPS_MANAGER)
    assert not Role.VIEWER.has_privilege(Role.MAINTENANCE_TECHNICIAN)


# ── Security helpers ─────────────────────────────────────────────


def test_password_hashing():
    """Hash and verify passwords correctly."""
    password = "MySecureP@ss1!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword1!", hashed)


def test_jwt_token_roundtrip():
    """Create and decode JWT tokens."""
    data = {"sub": "user-123", "org_id": "org-456", "role": "admin"}
    token = create_access_token(data=data)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["org_id"] == "org-456"
    assert payload["role"] == "admin"
    assert "exp" in payload


# ── Onboarding ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_onboarding_status_after_register(client: AsyncClient):
    """Onboarding status returns welcome step for new orgs."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Onboard Test",
            "org_slug": "onboard-test",
            "email": "onboard@test.com",
            "password": "StrongPass1!",
            "display_name": "OB",
        },
    )
    token = reg.json()["access_token"]

    resp = await client.get(
        "/api/v1/onboarding/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["finished"] is False
    assert data["current_step"] == "welcome"
    assert len(data["steps"]) == 5
