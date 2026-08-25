"""
Maintenance Dashboard API — aircraft status overview with gripes and flight-readiness.

GET /api/v1/maintenance/dashboard
  - Lists all aircraft with their status
  - For each aircraft, shows the most recent flight release's gripes,
    safe_for_flight status, and mission capability
  - Returns a structured dashboard object
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.aircraft import Aircraft
from app.models.flight_release import FlightRelease, ReleaseStatus
from app.models.user import User

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


def _json_safe(val: Any) -> list:
    """Safely coerce a JSON column value to a list."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


@router.get("/dashboard")
async def maintenance_dashboard(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Return a structured maintenance dashboard covering all aircraft in the
    user's organisation.

    Each entry includes the aircraft's status and, when available, the
    gripes (open / deferred), safe_for_flight flag, and mission capability
    from its most recent flight release.
    """
    org_id = current_user.organization_id

    # ── 1. Fetch all aircraft for this org ──────────────────────────────
    ac_stmt = (
        select(Aircraft)
        .where(Aircraft.organization_id == org_id)
        .order_by(Aircraft.tail_number)
    )
    ac_result = await db.execute(ac_stmt)
    aircraft_list = ac_result.scalars().all()

    if not aircraft_list:
        return {
            "aircraft": [],
            "total_aircraft": 0,
            "summary": _empty_summary(),
        }

    aircraft_ids = [a.id for a in aircraft_list]

    # ── 2. Most recent FlightRelease per aircraft ───────────────────────
    # Subquery: get the latest created_at per aircraft_id
    latest_subq = (
        select(
            FlightRelease.aircraft_id,
            sa_func.max(FlightRelease.created_at).label("latest_created"),
        )
        .where(
            FlightRelease.aircraft_id.in_(aircraft_ids),
            FlightRelease.status.in_(
                [ReleaseStatus.DRAFT, ReleaseStatus.RELEASED, ReleaseStatus.AMENDED]
            ),
        )
        .group_by(FlightRelease.aircraft_id)
        .subquery()
    )

    # Join to get full release rows matching the latest timestamp
    releases_stmt = (
        select(FlightRelease)
        .join(
            latest_subq,
            and_(
                FlightRelease.aircraft_id == latest_subq.c.aircraft_id,
                FlightRelease.created_at == latest_subq.c.latest_created,
            ),
        )
    )
    releases_result = await db.execute(releases_stmt)
    latest_releases: dict[str, FlightRelease] = {
        r.aircraft_id: r for r in releases_result.scalars().all()
    }

    # ── 3. Assemble dashboard ───────────────────────────────────────────
    dashboard_entries: list[dict[str, Any]] = []
    summary_counts = _empty_summary()

    for ac in aircraft_list:
        status_val = ac.status.value if ac.status else "unknown"
        release = latest_releases.get(ac.id)

        # Gripes from the most recent release
        gripes_open = _json_safe(release.gripes_open) if release else []
        gripes_deferred = _json_safe(release.gripes_deferred) if release else []

        safe_for_flight = release.safe_for_flight if release else False
        mission_cap = release.mission_capability.value if (release and release.mission_capability) else "unknown"

        has_open_gripes = any(
            g.get("status", "open") == "open"
            for g in gripes_open
        ) if gripes_open else False

        has_deferred = len(gripes_deferred) > 0

        entry: dict[str, Any] = {
            "aircraft_id": ac.id,
            "tail_number": ac.tail_number,
            "make": ac.make,
            "model": ac.model,
            "category": ac.category.value if ac.category else "",
            "status": status_val,
            "base_icao": ac.base,
            "safe_for_flight": safe_for_flight,
            "mission_capability": mission_cap,
            "gripes_open_count": len(gripes_open),
            "gripes_deferred_count": len(gripes_deferred),
            "has_open_gripes": has_open_gripes,
            "has_deferred_gripes": has_deferred,
            "latest_release_id": release.id if release else None,
            "latest_release_number": release.release_number if release else None,
            "latest_release_status": release.status.value if release else None,
            "gripes_open": gripes_open[:10],   # cap for dashboard
            "gripes_deferred": gripes_deferred[:10],
        }

        # ── Update summary counts ────────────────────────────────────────
        summary_counts["total_aircraft"] += 1
        if status_val == "active":
            summary_counts["active"] += 1
        elif status_val == "in_maintenance":
            summary_counts["in_maintenance"] += 1
        elif status_val == "grounded":
            summary_counts["grounded"] += 1

        if has_open_gripes:
            summary_counts["aircraft_with_open_gripes"] += 1
        if not safe_for_flight:
            summary_counts["aircraft_not_safe_for_flight"] += 1
        if has_deferred:
            summary_counts["aircraft_with_deferred_gripes"] += 1

        dashboard_entries.append(entry)

    return {
        "aircraft": dashboard_entries,
        "total_aircraft": len(dashboard_entries),
        "summary": summary_counts,
    }


def _empty_summary() -> dict[str, int]:
    return {
        "total_aircraft": 0,
        "active": 0,
        "in_maintenance": 0,
        "grounded": 0,
        "aircraft_with_open_gripes": 0,
        "aircraft_with_deferred_gripes": 0,
        "aircraft_not_safe_for_flight": 0,
    }
