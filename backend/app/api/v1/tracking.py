"""Live flight tracking via ADSB.lol API — Phase 1."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.aircraft import Aircraft
from app.models.user import User

router = APIRouter(prefix="/tracking", tags=["tracking"])

ADSB_API = "https://api.adsb.lol/v2/callsign"


@router.get("/live")
async def live_tracking(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get live positions for the user's aircraft fleet.

    Queries ADSB.lol for each tail number. Returns whatever positions
    are currently being broadcast (aircraft not in ADS-B range are omitted).
    """
    result = await db.execute(
        select(Aircraft.tail_number).where(
            Aircraft.organization_id == current_user.organization_id,
            Aircraft.status == "active",
        )
    )
    tails = [row[0] for row in result.all()]

    if not tails:
        return {"aircraft": [], "timestamp": None}

    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [client.get(f"{ADSB_API}/{tail}") for tail in tails]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    positions = []
    for tail, resp in zip(tails, responses):
        if isinstance(resp, Exception):
            continue
        if resp.status_code != 200:
            continue
        data = resp.json()
        ac_list = data.get("ac", [])
        if not ac_list:
            continue
        # Take the first match
        ac = ac_list[0]
        positions.append({
            "tail": tail,
            "lat": ac.get("lat"),
            "lon": ac.get("lon"),
            "altitude_ft": ac.get("alt_geom") or ac.get("alt_baro"),
            "speed_kts": ac.get("gs"),
            "heading": ac.get("track"),
            "callsign": (ac.get("flight") or "").strip(),
            "seen_seconds": ac.get("seen"),
            "rssi": ac.get("rssi"),
        })

    return {
        "aircraft": positions,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
