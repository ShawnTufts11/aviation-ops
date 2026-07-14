"""AI Help Desk — lightweight chat interface for querying ops data."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.permissions import require_org_membership
from app.models.user import User
from app.models.aircraft import Aircraft

router = APIRouter(prefix="/helpdesk", tags=["helpdesk"])


# ── Simple query parser ─────────────────────────────────────────

def _find_tail_number(text: str) -> str | None:
    """Extract a tail number from a query string."""
    patterns = [
        r"\b([A-Z]\d?-[A-Z]{3})\b",    # C6-PRD, N123AB
        r"\b([A-Z]{2}\d{3}[A-Z]{0,2})\b",  # N123AB
    ]
    for p in patterns:
        m = re.search(p, text.upper())
        if m:
            return m.group(1)
    return None


async def _answer_maintenance_query(
    question: str, tail: str, org_id: str, db: AsyncSession
) -> str:
    """Answer questions about maintenance history."""
    from app.models.aircraft import AircraftComponent
    from app.models.maintenance import MaintenanceTask

    q_lower = question.lower()

    # "When was the last oil change?"
    if "oil change" in q_lower or "oil" in q_lower:
        result = await db.execute(
            select(MaintenanceTask)
            .where(
                MaintenanceTask.aircraft_id == select(Aircraft.id).where(
                    Aircraft.tail_number == tail, Aircraft.organization_id == org_id
                ).scalar_subquery(),
                MaintenanceTask.title.ilike("%oil%"),
                MaintenanceTask.status == "completed",
            )
            .order_by(desc(MaintenanceTask.completed_date))
            .limit(1)
        )
        task = result.scalar_one_or_none()
        if task:
            return (
                f"Last oil change on **{tail}** was completed "
                f"{task.completed_date.strftime('%b %d, %Y') if task.completed_date else 'N/A'} "
                f"at {task.completed_hours or 'N/A'} hours."
            )
        return f"No oil change records found for {tail}."

    # "What maintenance is due?"
    if "due" in q_lower or "overdue" in q_lower or "upcoming" in q_lower:
        result = await db.execute(
            select(MaintenanceTask)
            .where(
                MaintenanceTask.aircraft_id == select(Aircraft.id).where(
                    Aircraft.tail_number == tail, Aircraft.organization_id == org_id
                ).scalar_subquery(),
                MaintenanceTask.status.in_(["scheduled", "overdue"]),
            )
            .order_by(MaintenanceTask.scheduled_date)
            .limit(5)
        )
        tasks = result.scalars().all()
        if tasks:
            lines = [f"Upcoming maintenance for **{tail}**:"]
            for t in tasks:
                status_icon = "🔴" if t.status == "overdue" else "🟡"
                lines.append(
                    f"  {status_icon} {t.title} — "
                    f"{'OVERDUE' if t.status == 'overdue' else t.scheduled_date or 'No date'}"
                )
            return "\n".join(lines)
        return f"No upcoming maintenance for {tail}."

    return None


async def _answer_general_query(
    question: str, org_id: str, db: AsyncSession
) -> str:
    """Answer general questions about the fleet."""
    q_lower = question.lower()

    # "How many aircraft do I have?"
    if "how many aircraft" in q_lower or "fleet size" in q_lower:
        result = await db.execute(
            select(func.count(Aircraft.id)).where(
                Aircraft.organization_id == org_id,
                Aircraft.status == "active",
            )
        )
        count = result.scalar() or 0
        return f"You have **{count} active aircraft** in your fleet."

    # "What aircraft do I have?" or "list my aircraft"
    if "list" in q_lower or "aircraft do i have" in q_lower or "my fleet" in q_lower:
        result = await db.execute(
            select(Aircraft).where(Aircraft.organization_id == org_id).limit(10)
        )
        aircraft = result.scalars().all()
        if aircraft:
            lines = ["**Your fleet:**"]
            for a in aircraft:
                status_icon = "✅" if a.status == "active" else "🔧" if a.status == "in_maintenance" else "⛔"
                lines.append(f"  {status_icon} **{a.tail_number}** — {a.make} {a.model} ({a.status})")
            return "\n".join(lines)
        return "No aircraft registered yet."

    # "Summary" or "overview"
    if "summary" in q_lower or "overview" in q_lower:
        result = await db.execute(
            select(Aircraft.status, func.count(Aircraft.id))
            .where(Aircraft.organization_id == org_id)
            .group_by(Aircraft.status)
        )
        rows = result.all()
        total = sum(r[1] for r in rows)
        statuses = {r[0]: r[1] for r in rows}
        return (
            f"**Fleet Summary:** {total} total aircraft. "
            f"{statuses.get('active', 0)} active, "
            f"{statuses.get('in_maintenance', 0)} in maintenance, "
            f"{statuses.get('grounded', 0)} grounded."
        )

    return None


from pydantic import BaseModel


class HelpdeskQuery(BaseModel):
    question: str


@router.post("/ask")
async def ask_helpdesk(
    body: HelpdeskQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Ask a question about your aviation operations.

    Examples:
      - "When was the last oil change on C6-PRD?"
      - "What maintenance is due?"
      - "How many aircraft do I have?"
      - "List my fleet"
    """
    question = body.question
    if not question or not question.strip():
        return {"answer": "Please ask a question.", "sources": []}

    org_id = current_user.organization_id
    tail = _find_tail_number(question)

    # Try maintenance-specific queries first (need a tail number)
    if tail:
        answer = await _answer_maintenance_query(question, tail, org_id, db)
        if answer:
            return {"answer": answer, "sources": ["maintenance"]}

    # Try general fleet queries
    answer = await _answer_general_query(question, org_id, db)
    if answer:
        return {"answer": answer, "sources": ["fleet"]}

    # Fallback
    return {
        "answer": (
            "I can answer questions about your fleet and maintenance. Try:\n"
            "  • \"How many aircraft do I have?\"\n"
            "  • \"List my fleet\"\n"
            "  • \"When was the last oil change on C6-PRD?\"\n"
            "  • \"What maintenance is due on C6-PRD?\"\n"
            "  • \"Fleet summary\""
        ),
        "sources": [],
    }
