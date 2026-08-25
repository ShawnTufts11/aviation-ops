# ParaRig Aviation Operations Suite

A modern, white-label aviation management system for Part 135 on-demand charter, cargo, and personnel transport operations. Built for the real-world demands of international Caribbean operations (Nassau ↔ Haiti and beyond).

## Architecture

```
pararig-ops/
├── backend/                        # FastAPI + SQLAlchemy 2.0 (Python 3.12)
│   ├── app/
│   │   ├── api/v1/                 # 31 route modules
│   │   │   ├── auth.py             # JWT + MFA authentication
│   │   │   ├── onboarding.py       # Invite codes, org creation wizard
│   │   │   ├── helpdesk.py         # In-app AI help desk
│   │   │   ├── admin.py            # Super-admin controls
│   │   │   ├── users.py            # User management
│   │   │   ├── permissions.py      # RBAC permission overrides
│   │   │   ├── org_settings.py     # Organization settings
│   │   │   ├── aircraft.py         # Aircraft CRUD + status
│   │   │   ├── airports.py         # Airport database
│   │   │   ├── routes.py           # Route planner (POST /api/v1/routes/plan)
│   │   │   ├── flights.py          # Flight scheduling & dispatch
│   │   │   ├── missions.py         # Multi-leg mission planning
│   │   │   ├── passengers.py       # Passenger manifest
│   │   │   ├── flight_releases.py  # 3-gate signoff workflow
│   │   │   ├── ops_checks.py       # Operational checks
│   │   │   ├── crew.py             # Crew profiles & qualifications
│   │   │   ├── logbook.py          # Crew logbook entries
│   │   │   ├── maintenance.py      # Task library & interval tracking
│   │   │   ├── maintenance_dashboard.py  # Maintenance overview
│   │   │   ├── compliance.py       # Document & regulatory tracking
│   │   │   ├── comms.py            # WebSocket notification bus
│   │   │   ├── tracking.py         # Live ADS-B tracking
│   │   │   ├── weather_router.py   # METAR/TAF/NOTAM endpoints
│   │   │   ├── finance.py          # P&L per tail, cost tracking
│   │   │   ├── costs.py            # Cost tracking
│   │   │   ├── leg_costs.py        # Leg-level cost breakdown
│   │   │   ├── briefing.py         # Morning brief dashboard
│   │   │   ├── reports.py          # Reporting & export
│   │   │   ├── bulk_import.py      # CSV bulk import
│   │   │   └── export.py           # Data export
│   │   ├── core/                   # Config, DB, security, audit, RBAC
│   │   │   ├── config.py           # Pydantic settings
│   │   │   ├── database.py         # SQLAlchemy async engine
│   │   │   ├── security.py         # JWT, MFA, password hashing
│   │   │   ├── audit.py            # Audit logging
│   │   │   ├── roles.py            # 11 FAA Part 135 role levels
│   │   │   ├── features.py         # Feature flags (26 features, 12 categories)
│   │   │   └── permissions.py      # Permission resolution
│   │   ├── models/                 # 18 SQLAlchemy ORM models
│   │   │   ├── organization.py     # Multi-tenant org isolation
│   │   │   ├── user.py             # Users with per-user permission overrides
│   │   │   ├── invite.py           # Invite codes with multi-role support
│   │   │   ├── aircraft.py         # Aircraft registry & components
│   │   │   ├── airport.py          # ICAO airport database
│   │   │   ├── flight.py           # Flight legs
│   │   │   ├── flight_release.py   # Flight release with 3-gate signoff
│   │   │   ├── mission.py          # Multi-leg missions
│   │   │   ├── passenger.py        # Passenger manifests
│   │   │   ├── crew.py             # Crew profiles, quals, duty time
│   │   │   ├── logbook.py          # Pilot logbook entries
│   │   │   ├── maintenance.py      # Tasks, intervals, deferred items
│   │   │   ├── document.py         # Document registry + expiration
│   │   │   ├── notification.py     # Notification records
│   │   │   ├── finance.py          # Financial entries
│   │   │   ├── leg_cost.py         # Leg-level costs
│   │   │   └── audit.py            # Audit trail
│   │   ├── schemas/                # Pydantic request/response models
│   │   └── services/               # 9 business logic modules
│   │       ├── route_planner.py    # Route intel per leg
│   │       ├── weather.py          # AviationWeather.gov METAR/TAF
│   │       ├── ad_compliance.py    # AD/SB airworthiness compliance
│   │       ├── weight_balance.py   # Per-leg W&B against MTOW/MLW/ZFW
│   │       ├── crew_duty.py        # FAR 135.267 flight/duty/rest limits
│   │       ├── airport_lookup.py   # Airport search & details
│   │       ├── distance.py         # Great-circle distance calculations
│   │       ├── flight_performance.py  # Phase-based performance estimates
│   │       └── __init__.py
│   ├── alembic/                    # Database migrations
│   └── tests/                      # Pytest test suite
├── frontend/                       # Vite + React 18 + TypeScript + Tailwind
│   ├── src/
│   │   ├── app/
│   │   │   ├── pages/              # 26 page modules
│   │   │   │   ├── auth/           # Login, Register, AcceptInvite
│   │   │   │   ├── fleet/          # FleetPage, AircraftDetail
│   │   │   │   ├── flights/        # FlightsPage, MissionBuilder, Dispatch
│   │   │   │   ├── maintenance/    # MaintenancePage, MaintControlPage
│   │   │   │   ├── crew/           # CrewPage, CrewDetail
│   │   │   │   ├── compliance/     # CompliancePage
│   │   │   │   ├── finance/        # FinancePage
│   │   │   │   ├── operations/     # OperationCenterPage
│   │   │   │   ├── briefing/       # MorningBriefPage
│   │   │   │   ├── admin/          # AdminPage, UsersAdmin, Settings
│   │   │   │   └── ...             # AirportLookup, Passengers, etc.
│   │   │   ├── layout/             # RootLayout, Sidebar, TopBar
│   │   │   └── routing/
│   │   ├── features/               # Feature modules
│   │   │   ├── auth/               # AuthContext, useAuth, AuthGuard
│   │   │   ├── tracking/           # LiveTrackingMap (MapLibre GL)
│   │   │   ├── map/                # RouteMap component
│   │   │   ├── costs/              # CostsPnlSection, CostLogForm
│   │   │   ├── onboarding/         # OnboardingWizard
│   │   │   └── helpdesk/           # HelpdeskPanel (in-app AI chat)
│   │   └── components/             # Shared shadcn/ui components
│   ├── public/                     # PWA assets
│   └── dist/                       # Production build output
├── deploy/
│   ├── .env.example
│   ├── Caddyfile
│   ├── docker-compose.yml          # (skeleton — project not yet Dockerized)
│   └── scripts/
│       ├── seed-foundation.py      # Core reference data (airports, perf profiles)
│       ├── seed-data.py            # General demo data
│       ├── seed-comprehensive-demo.py  # Full demo with realistic ops
│       ├── seed-test-scenario.py   # Test scenario data
│       └── seed-for-user.py        # Seed data for a specific user
└── docs/
    └── SPEC.md                     # Full system specification
```

## Quick Start (Development)

```bash
# 1. Clone and go to project root
cd ~/projects/pararig-ops

# 2. Backend — setup and run
cd backend
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8100

# 3. Frontend — separate terminal
cd frontend
npm install
npm run dev

# 4. Seed foundation data (airports, aircraft performance profiles)
cd backend
uv run python ../deploy/scripts/seed-foundation.py
```

Then visit `http://localhost:5173` for the frontend dashboard (backend API at `http://localhost:8100`).

## Modules

| # | Module | Status |
|---|--------|--------|
| 1 | Auth & Organization | **DONE** — JWT/MFA/RBAC, 11 FAA Part 135 roles, org settings, invite codes with multi-role support, bulk import |
| 2 | Fleet Configuration | **DONE** — Aircraft CRUD, component tracking, CSV import, status tracking |
| 3 | Maintenance Tracking | **DONE** — Task library, interval tracking, AD/SB compliance, maintenance dashboard, deferred workflow |
| 4 | Flight Operations & Missions | **DONE** — Multi-leg mission planning, route planner (POST /api/v1/routes/plan), flight releases with 3-gate signoff, ops checks |
| 5 | Crew / Personnel | **DONE** — Crew profiles, qualifications with expiry, duty time (FAR 135.267), logbook |
| 6 | Compliance & Documents | **DONE** — Document tracking, expiration management, compliance checklist per route |
| 7 | Financial Dashboard | **DONE** — P&L per tail, cost tracking, leg-level costs, estimated vs actual |
| 8 | Operation Center | **DONE** — Live ADS-B tracking map (MapLibre GL), 10 toggleable layers, weather radar, NOTAM overlays, emergency alerts |
| 9 | Comms & Emergency Alerting | **DONE** — WebSocket notification bus, emergency alert button, escalation |
| 10 | Weight & Balance | **DONE** — Per-leg W&B against aircraft limits (MTOW/MLW/ZFW) |
| 11 | Crew Duty Time | **DONE** — FAR 135.267 flight/duty/rest limits |
| 12 | AD/SB Compliance | **DONE** — Fleet-wide airworthiness tracking with severity-grounded logic |
| 13 | Weather Integration | **DONE** — AviationWeather.gov METAR/TAF, FAA NMS NOTAMs |
| 14 | Morning Brief | **DONE** — Role-gated 7-card ops briefing dashboard |
| 15 | RBAC & Permissions | **DONE** — 26 features across 12 categories, per-user overrides |
| 16 | Onboarding Module | **DONE** — Invite codes, org creation wizard |
| 17 | AI Help Desk | **DONE** — In-app chat interface
| 18 | Route Planner | **DONE** — POST /api/v1/routes/plan, full intel per leg |
| 19 | White-Label / Multi-Tenant | **Phase 2** — Custom branding, subdomain, feature flags per tenant |

## Key Features

- **Multi-tenant:** Organizations fully isolated at database level (org_id on every table)
- **FAA Part 135 RBAC:** 11 role levels from Super Admin → ReadOnly, 26 features across 12 categories, per-user permission overrides
- **MFA:** TOTP-based two-factor authentication
- **Flight Operations:** Multi-leg mission planning with route intel, 3-gate flight release signoff, weight & balance per leg
- **Maintenance:** Task library with interval tracking, AD/SB compliance with severity-grounded logic, deferred maintenance workflow, dashboard overview
- **Crew Management:** Qualifications with expiry dates, FAR 135.267 duty/flight/rest limit tracking, pilot logbook
- **Live Operation Center:** Real-time ADS-B tracking via MapLibre GL with 10 toggleable layers, weather radar overlay, NOTAM overlays, emergency alerts
- **Weather & NOTAMs:** METAR/TAF via AviationWeather.gov, NOTAMs via FAA NMS API
- **Financial Dashboard:** P&L per tail number, leg-level cost breakdown, estimated vs actual cost reconciliation
- **Compliance:** Document registry with expiration tracking, compliance checklist per route, automated expiry alerts. **Expiry Center** (`GET /api/v1/compliance/expiry-center`) aggregates aircraft/component/crew/qualification/document/AD-SB expiries into one read-only view, feeding the daily **Compliance Watch** Discord alert (08:20, #command-center). See `EXPIRY_CENTER_SCOPE.md`.
- **Emergency Alerting:** One-tap escalation with WebSocket push, notification bus
- **Morning Brief:** Role-gated 7-card ops briefing dashboard with current-day snapshot
- **AI Help Desk:** In-app chat interface for operations assistance
- **Route Planner:** Full intel per leg including distances, alternate airports, estimated fuel burn, and flight time
- **Dark mode first:** Designed for ops centers and field iPads
- **PWA ready:** Offline-capable for crews in the field

## Environment

Developed on ParaRig infrastructure (The Citadel).
Deploys as Docker compose on any Linux host with Tailscale (coming soon — Docker setup is skeleton).

## License

ParaRig Dynamics — Proprietary. Self-hosted license or SaaS subscription.
