"""
ParaRig Aviation Operations Suite — FastAPI application entry point.

Creates the ASGI application, mounts middleware, includes routers,
and manages lifecycle (DB init on startup, engine disposal on shutdown).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import engine, init_db


# ── API v1 Router ──────────────────────────────────────────────────────────
# Lazy-imported inside lifespan to avoid circular imports at module level.


def _build_v1_router() -> FastAPI:
    """Build and return the v1 API sub-application with all routers mounted."""
    from fastapi import APIRouter

    from app.api.v1 import auth
    from app.api.v1 import onboarding
    from app.api.v1 import helpdesk
    from app.api.v1 import aircraft
    from app.api.v1 import airports
    from app.api.v1 import routes
    from app.api.v1 import maintenance
    from app.api.v1 import flights
    from app.api.v1 import crew
    from app.api.v1 import compliance
    from app.api.v1 import comms
    from app.api.v1 import finance
    from app.api.v1 import tracking
    from app.api.v1 import ops_checks
    from app.api.v1 import missions
    from app.api.v1 import passengers
    from app.api.v1 import users
    from app.api.v1 import org_settings
    from app.api.v1 import admin
    from app.api.v1 import bulk_import
    from app.api.v1 import export
    from app.api.v1 import logbook
    from app.api.v1 import reports

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(auth.router)
    api_v1.include_router(onboarding.router)
    api_v1.include_router(helpdesk.router)
    api_v1.include_router(aircraft.router)
    api_v1.include_router(airports.router)
    api_v1.include_router(routes.router)
    api_v1.include_router(maintenance.router)
    api_v1.include_router(flights.router)
    api_v1.include_router(crew.router)
    api_v1.include_router(compliance.router)
    api_v1.include_router(comms.router)
    api_v1.include_router(finance.router)
    api_v1.include_router(tracking.router)
    api_v1.include_router(ops_checks.router)
    api_v1.include_router(missions.router)
    api_v1.include_router(passengers.router)
    api_v1.include_router(users.router)
    api_v1.include_router(org_settings.router)
    api_v1.include_router(admin.router)
    api_v1.include_router(bulk_import.router)
    api_v1.include_router(export.router)
    api_v1.include_router(logbook.router)
    api_v1.include_router(reports.router)
    return api_v1


# ── Lifespan ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown."""
    # ── Startup ───────────────────────────────────────────────────────────
    if settings.is_dev:
        await init_db()
    yield
    # ── Shutdown ──────────────────────────────────────────────────────────
    await engine.dispose()


# ── App Factory ────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "auth", "description": "Authentication and user management"},
            {"name": "aircraft", "description": "Aircraft registry and status"},
            {"name": "flights", "description": "Flight scheduling and dispatch"},
            {"name": "maintenance", "description": "Maintenance tracking and logs"},
            {"name": "crew", "description": "Crew management and qualifications"},
            {"name": "compliance", "description": "Regulatory and compliance records"},
            {"name": "finance", "description": "Financials, invoices, and reports"},
            {"name": "dashboard", "description": "Operational dashboards and KPIs"},
            {"name": "admin", "description": "System administration (super-admin)"},
        ],
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.is_prod:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
        )

    # ── Routes ────────────────────────────────────────────────────────────
    v1_router = _build_v1_router()
    app.include_router(v1_router)  # already has /api/v1 prefix

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint — returns 200 when the app is running."""
        return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}

    return app


# ── ASGI entry point ───────────────────────────────────────────────────────
app = create_app()
