"""
Security utilities: JWT creation/validation, password hashing, MFA, invite tokens.

All auth primitives used throughout the application live here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from itsdangerous import URLSafeTimedSerializer
from jose import JWTError, jwt
import bcrypt as _bcrypt
import pyotp

from app.core.config import settings

# ── Password hashing ───────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*."""
    return _bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )

# ── Invite token serializer ────────────────────────────────────────────────


# ── JWT helpers ────────────────────────────────────────────────────────────
def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    timeout_minutes: int | None = None,
) -> str:
    """Create a short-lived JWT access token.

    If *timeout_minutes* is provided it overrides the config default.
    Clamped to max 480 minutes (8 hours).
    Payload includes ``sub`` (user id), ``org_id``, ``role``, and ``exp``.
    """
    to_encode = data.copy()
    if timeout_minutes:
        timeout_minutes = min(timeout_minutes, 480)
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=timeout_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a longer-lived refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT. Returns the payload or *None* on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


# ── MFA / TOTP helpers ─────────────────────────────────────────────────────
def generate_mfa_secret(email: str = "") -> tuple[str, str]:
    """Generate a new base32-encoded TOTP secret and its provisioning URI.

    Returns (secret, provisioning_uri).
    """
    secret = pyotp.random_base32()
    if email:
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=email, issuer_name=settings.APP_NAME)
    else:
        uri = ""
    return secret, uri


def verify_mfa_totp(secret: str, token: str) -> bool:
    """Verify a TOTP code against the given secret. Tolerance = 1 step."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)


def get_mfa_provisioning_uri(secret: str, email: str) -> str:
    """Generate a provisioning URI for QR-code display."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.APP_NAME)


# ── Invite token helpers ───────────────────────────────────────────────────
invite_serializer = URLSafeTimedSerializer(
    secret_key=settings.SECRET_KEY,
    salt="invite-token",
)


def generate_invite_token(email: str, org_id: str, role: str = "pilot") -> str:
    """Sign an invite token embedding *email*, *org_id*, and *role*."""
    return invite_serializer.dumps({"email": email, "org_id": org_id, "role": role})


def verify_invite_token(
    token: str,
    max_age_seconds: int = 86400 * 7,
) -> Optional[dict[str, Any]]:
    """Verify an invite token. Returns payload or *None* if invalid/expired."""
    try:
        return invite_serializer.loads(token, max_age=max_age_seconds)
    except Exception:
        return None
