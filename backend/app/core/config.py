"""
Core configuration for the ParaRig Aviation Operations Suite.

Uses Pydantic Settings with environment variable / .env file support.
All secrets and environment-specific values are configured here.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./pararig_ops.db"

    # ── Auth / JWT ────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-a-real-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MFA_ENCRYPTION_KEY: str = "change-me-mfa-encryption-key-32chr!"

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["*"]

    # ── Environment ───────────────────────────────────────────────────────
    ENVIRONMENT: str = "dev"  # "dev" | "prod"
    INSTANCE_MODE: str = "self_hosted"  # "self_hosted" | "saas"

    # ── SMTP (optional) ───────────────────────────────────────────────────
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_USE_TLS: bool = True

    # ── Twilio SMS (optional) ─────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None

    # ── App metadata ──────────────────────────────────────────────────────
    APP_NAME: str = "ParaRig Ops"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    @property
    def is_prod(self) -> bool:
        """Return True if running in production mode."""
        return self.ENVIRONMENT.lower() == "prod"

    @property
    def is_dev(self) -> bool:
        """Return True if running in development mode."""
        return self.ENVIRONMENT.lower() == "dev"

    @property
    def sync_database_url(self) -> str:
        """Return a sync-compatible database URL (for Alembic etc.)."""
        return self.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a list — handles wildcard correctly."""
        return self.CORS_ORIGINS if self.CORS_ORIGINS else ["*"]


settings = Settings()
