# ParaRig Aviation Operations Suite

A modern, white-label aviation management system for Part 135 on-demand charter, cargo, and personnel transport operations. Built for the real-world demands of international Caribbean operations (Nassau ↔ Haiti and beyond).

## Architecture

```
pararig-ops/
├── backend/          # FastAPI + SQLAlchemy 2.0 (Python 3.12)
│   ├── app/
│   │   ├── api/      # Route handlers (v1)
│   │   ├── core/     # Config, DB, security, audit, RBAC
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic request/response models
│   │   └── services/ # Business logic
│   ├── alembic/      # Database migrations
│   └── tests/
├── frontend/         # Vite + React 18 + TypeScript + Tailwind
│   ├── src/
│   │   ├── app/      # Layout, pages, routing
│   │   ├── features/ # Feature modules (auth, fleet, etc.)
│   │   └── components/ # Shared UI (shadcn/ui)
│   └── public/       # PWA assets
├── deploy/
│   ├── docker-compose.yml
│   ├── Caddyfile
│   ├── .env.example
│   └── scripts/      # seed-data.py, init-db.sh
└── docs/
    └── SPEC.md       # Full system specification
```

## Quick Start (Development)

```bash
# 1. Clone and go to project root
cd ~/projects/pararig-ops

# 2. Backend — setup and run
cd backend
uv venv
source .venv/bin/activate
uv pip install -e .
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Frontend — separate terminal
cd frontend
npm install
npm run dev

# 4. Seed demo data
python deploy/scripts/seed-data.py
```

## Quick Start (Docker)

```bash
cd deploy
cp .env.example .env
# Edit .env — set DB_PASSWORD and SECRET_KEY
docker compose up -d
```

Then visit `http://localhost` for the dashboard.

## Modules

| # | Module | Status |
|---|--------|--------|
| 1 | Auth & Organization Setup | Building |
| 2 | Fleet Configuration | Planned |
| 3 | Maintenance Tracking | Planned |
| 4 | Flight Operations & Scheduling | Planned |
| 5 | Crew Management | Planned |
| 6 | Compliance & Documents (BCAA/Haiti/US) | Planned |
| 7 | Financial Dashboard | Planned |
| 8 | Operation Center (w/ ADS-B Map) | Planned |
| 9 | Comms & Emergency Alerting | Planned |
| 10 | Onboarding Wizard | Planned |
| 11 | AI Help Desk | Planned |
| 12 | White-Label / Multi-Tenant | Phase 2 |

## Key Features

- **Multi-tenant:** Organizations fully isolated at database level
- **RBAC:** Super Admin → ReadOnly, 6 role levels
- **MFA:** TOTP-based two-factor authentication
- **International compliance:** BCAA, Haiti (MTTP), US (eAPIS), Caribbean waivers
- **ADS-B tracking:** Live fleet position via ADSB.lol / OpenSky + MapLibre GL
- **Auto-finance:** Flights auto-generate P&L entries per tail number
- **Emergency alerting:** One-tap escalation with WebSocket push
- **Dark mode first:** Designed for ops centers and field iPads
- **PWA ready:** Offline-capable for crews in the field
- **White-label:** Custom branding, subdomain, feature flags per tenant

## Environment

Developed on ParaRig infrastructure (The Citadel).  
Deploys as Docker compose on any Linux host with Tailscale.

## License

ParaRig Dynamics — Proprietary. Self-hosted license or SaaS subscription.
