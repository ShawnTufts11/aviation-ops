"""
AuditLog model — immutable record of every state-changing action.

Required for Part 135 compliance. Every create, update, delete operation
should produce an audit log entry.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="e.g. created, updated, deleted"
    )
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="e.g. aircraft, flight"
    )
    entity_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    old_values: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    new_values: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.entity_type}#{self.entity_id}>"
