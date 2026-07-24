"""Onboarding wizard endpoints — multi-step org setup flow."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

ONBOARDING_STEPS = [
    {"id": "welcome", "label": "Welcome", "description": "Name your organization"},
    {"id": "aircraft", "label": "Add Aircraft", "description": "Register your first aircraft"},
    {"id": "crew", "label": "Add Crew", "description": "Add your first crew member"},
    {"id": "compliance", "label": "Compliance", "description": "Upload initial compliance documents"},
    {"id": "complete", "label": "Done", "description": "You're all set!"},
]


async def _resolve_org(
    current_user: User, db: AsyncSession
) -> Organization | None:
    """Resolve the user's organization, returning None if not yet assigned."""
    if current_user.organization_id is None:
        return None
    return await db.get(Organization, current_user.organization_id)


def _default_status() -> dict[str, Any]:
    """Return a default 'not started' onboarding status."""
    return {
        "finished": False,
        "current_step": "welcome",
        "completed_steps": [],
        "steps": ONBOARDING_STEPS,
        "progress_pct": 0,
    }


@router.get("/status")
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the organization's current onboarding state.

    If the user does not yet belong to an organization, returns a default
    'not started' state so the wizard can still render.
    """
    org = await _resolve_org(current_user, db)
    if not org:
        return _default_status()

    onboarding = org.settings.get("onboarding", {})
    completed_steps = onboarding.get("completed_steps", [])
    current_step = onboarding.get("current_step", "welcome")
    finished = onboarding.get("finished", False)

    return {
        "finished": finished,
        "current_step": current_step,
        "completed_steps": completed_steps,
        "steps": ONBOARDING_STEPS,
        "progress_pct": round(
            (len(completed_steps) / len(ONBOARDING_STEPS)) * 100, 0
        ) if not finished else 100,
    }


@router.post("/step")
async def complete_step(
    step_id: str,
    step_data: dict[str, Any] = {},
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark a step as completed and advance to the next.

    When the *welcome* step is completed with ``org_name`` in *step_data*,
    the organization's name and timezone are persisted immediately.
    """
    org = await _resolve_org(current_user, db)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must belong to an organization before completing onboarding steps",
        )

    # Validate step exists
    step_ids = [s["id"] for s in ONBOARDING_STEPS]
    if step_id not in step_ids:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step_id}")

    onboarding = dict(org.settings.get("onboarding", {}))
    completed_steps = list(onboarding.get("completed_steps", []))

    if step_id in completed_steps:
        return {
            "message": "Step already completed",
            "current_step": onboarding.get("current_step", "welcome"),
            "finished": onboarding.get("finished", False),
        }

    # ── Persist org-level settings from the welcome step ────────────────
    if step_id == "welcome":
        org_name = step_data.get("org_name")
        if org_name and isinstance(org_name, str) and org_name.strip():
            org.name = org_name.strip()
        timezone = step_data.get("timezone")
        if timezone and isinstance(timezone, str) and timezone.strip():
            org.timezone = timezone.strip()
        currency = step_data.get("currency")
        if currency and isinstance(currency, str) and currency.strip():
            org.currency = currency.strip().upper()

    # Save step data if provided
    step_data_storage = dict(onboarding.get("step_data", {}))
    step_data_storage[step_id] = step_data
    onboarding["step_data"] = step_data_storage

    # Mark step as completed
    completed_steps.append(step_id)
    onboarding["completed_steps"] = completed_steps

    # Find next step
    current_idx = step_ids.index(step_id)
    if current_idx + 1 < len(step_ids):
        next_step = step_ids[current_idx + 1]
        onboarding["current_step"] = next_step
    else:
        onboarding["current_step"] = "complete"
        onboarding["finished"] = True

    org.settings = {**org.settings, "onboarding": onboarding}
    db.add(org)
    await db.commit()

    return {
        "message": f"Step '{step_id}' completed",
        "current_step": onboarding["current_step"],
        "finished": onboarding.get("finished", False),
        "progress_pct": round((len(completed_steps) / len(ONBOARDING_STEPS)) * 100, 0),
    }


@router.post("/skip")
async def skip_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Skip the onboarding wizard entirely."""
    org = await _resolve_org(current_user, db)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must belong to an organization before skipping onboarding",
        )

    onboarding = dict(org.settings.get("onboarding", {}))
    onboarding["finished"] = True
    onboarding["current_step"] = "complete"
    onboarding["completed_steps"] = [s["id"] for s in ONBOARDING_STEPS]
    onboarding["skipped"] = True

    org.settings = {**org.settings, "onboarding": onboarding}
    db.add(org)
    await db.commit()

    return {"message": "Onboarding skipped", "finished": True}
