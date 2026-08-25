"""InviteCode model — registration requires a valid invite code."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InviteCode(Base):
    """One-time invite code for registering or joining an organization."""

    __tablename__ = "invite_codes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
        comment="Human-readable code sent to the invitee",
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        comment="If set, user joins this org. If null, code creates a new org.",
    )
    role: Mapped[str] = mapped_column(
        String(32), default="viewer", nullable=False,
        comment="Role granted (admin for new-org invites, pilot/dispatcher etc. for joining)",
    )

    # ── Multi-role / feature-scoped invites ───────────────────────────────
    allowed_roles: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True,
        comment="List of roles the invitee can choose from (null = single role only)",
    )
    granted_features: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False,
        comment="Additional feature overrides granted to the user upon accepting (e.g. [\"pii:access\"])",
    )
    max_uses: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False,
        comment="Maximum number of times this code can be used (1 = single-use, 0 = unlimited)",
    )
    use_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Number of times this code has been used",
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Internal note about what this invite code is for",
    )

    # Usage tracking
    used_by: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="User ID of who used it"
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Expiry
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Code expires after this date",
    )

    # Audit
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<InviteCode {self.code} used={self.is_used}>"
