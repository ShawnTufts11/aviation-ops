# ParaRig Aviation Operations Suite — Full Specification

**Project:** Aviation Operations Management System (Ops VP)
**Client:** ParaRig Dynamics / Private Aviation Operation (Nassau ↔ Haiti)
**Version:** 1.0 — Blueprint
**Date:** 2026-07-14
**Author:** Hermes (The Citadel) + Grok + Shawn

---

## 1. Vision Statement

A white-label, turnkey aviation management suite that feels modern and intuitive — not like the legacy ERP systems that dominate this space (AvPro, FlightDocs, etc.). Unifies maintenance scheduling, flight operations, crew management, compliance, and financial tracking into a single pane of glass.

**Core philosophy:** A pilot should be able to log their flight, a mechanic should see the inspection due, the Ops VP should see the P&L, and the compliance officer should see the upcoming renewal — all from the same system, in real time, without spreadsheets or sticky notes.

**Business model:** Dual-track — self-hosted license for operators who want on-prem control, SaaS subscription for those who don't. White-label ready.

---

## 2. Architecture Overview

### 2.1 Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Backend** | FastAPI (Python 3.12+) | Async, auto-OpenAPI, fast to build, easy to audit |
| **Database** | PostgreSQL 16 (primary) / SQLite (dev/demo fallback) | SQLite for single-user dev, PG for production multi-user |
| **ORM** | SQLAlchemy 2.0 + Alembic | Mature, async-ready, migration-driven schema |
| **Frontend** | React 18 + TypeScript + Tailwind CSS 4 | PWA-capable, mobile-first, modern UX |
| **State / Data** | TanStack Query + Zustand | Server-state caching + lightweight client state |
| **UI Components** | shadcn/ui + Radix Primitives | Accessible, composable, Tailwind-native |
| **Maps** | MapLibre GL (open-source) | Self-hosted tile server option, no Google dependency |
| **Charts** | Apache ECharts (via echarts-for-react) | Rich charting, self-hostable |
| **Auth** | FastAPI Users + JWT + MFA (TOTP) | Battle-tested, extendable |
| **Queue / Async** | Celery + Redis (optional, for heavy PDF gen / notifications) | Not MVP-essential, add when needed |
| **Container** | Docker + docker-compose | Single `docker compose up` to deploy |
| **Reverse Proxy** | Caddy (auto-TLS) | Simpler than nginx + certbot, built-in Let's Encrypt |
| **Fleet Tracking** | ADSB.lol / OpenSky API / optional dump1090 feed | WebSocket-based aircraft position feed |
| **Payments** | Stripe (for SaaS) | Billing, invoicing, recurring |

### 2.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Caddy (TLS Proxy)                  │
│              *.opspanel.local / ops.pararig.com      │
├──────────────────────┬──────────────────────────────┤
│      Frontend        │         Backend API            │
│   React + Tailwind   │    FastAPI + SQLAlchemy        │
│   Vite (build)       │    uvicorn (serve)             │
│   PWA (offline)      │    Celery (background jobs)    │
├──────────────────────┴──────────────────────────────┤
│                 PostgreSQL 16                         │
│    (or SQLite for single-user / dev mode)             │
├──────────────────────┬──────────────────────────────┤
│   Redis (optional)   │     File Storage (S3/Minio)   │
│   (queue + cache)    │     (docs, logsheets, etc.)   │
└──────────────────────┴──────────────────────────────┘
```

### 2.3 Data Flow Principles

1. **Every flight generates a financial record** — auto-calculated cost vs revenue by tail number
2. **Every maintenance event generates a log entry** — GPS-stamped, user-attributed
3. **Every document has a reminder** — expiration tracking with configurable lead time
4. **Every crew member has a currency dashboard** — hours, medicals, training, quals at a glance
5. **All changes are audited** — immutable audit log with who-did-what-when

### 2.4 Directory Structure

```
pararig-ops/
├── backend/
│   ├── app/
│   │   ├── api/                    # Route handlers
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── aircraft.py
│   │   │   │   ├── flights.py
│   │   │   │   ├── maintenance.py
│   │   │   │   ├── crew.py
│   │   │   │   ├── compliance.py
│   │   │   │   ├── finance.py
│   │   │   │   ├── dashboard.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── settings.py
│   │   │   │   └── scheduling.py
│   │   │   └── deps.py             # Dependency injection
│   │   ├── core/
│   │   │   ├── config.py           # Settings from env
│   │   │   ├── database.py         # SQLAlchemy engine + session
│   │   │   ├── security.py         # JWT, MFA, password hashing
│   │   │   ├── audit.py            # Audit log middleware
│   │   │   └── permissions.py      # RBAC decorators
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── aircraft.py
│   │   │   ├── flights.py
│   │   │   ├── maintenance.py
│   │   │   ├── crew.py
│   │   │   ├── compliance.py
│   │   │   ├── finance.py
│   │   │   ├── documents.py
│   │   │   ├── scheduling.py
│   │   │   └── auth.py
│   │   ├── schemas/                # Pydantic models (request/response)
│   │   │   ├── aircraft.py
│   │   │   ├── flights.py
│   │   │   └── ...
│   │   ├── services/               # Business logic layer
│   │   │   ├── flight_costing.py
│   │   │   ├── maintenance_forecast.py
│   │   │   ├── duty_time.py
│   │   │   └── ...
│   │   └── main.py                 # FastAPI app factory
│   ├── alembic/                    # Database migrations
│   ├── tests/
│   ├── alembic.ini
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                    # Route pages
│   │   ├── components/             # Shared UI components
│   │   ├── features/               # Feature modules
│   │   │   ├── auth/
│   │   │   ├── fleet/
│   │   │   ├── flights/
│   │   │   ├── maintenance/
│   │   │   ├── crew/
│   │   │   ├── compliance/
│   │   │   ├── finance/
│   │   │   ├── dashboard/
│   │   │   └── operations-center/
│   │   ├── hooks/                  # Custom React hooks
│   │   ├── lib/                    # Utilities
│   │   └── types/                  # TypeScript types
│   ├── public/                     # PWA assets
│   ├── tailwind.config.ts
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── package.json
├── deploy/
│   ├── docker-compose.yml
│   ├── Caddyfile
│   ├── .env.example
│   └── scripts/
│       ├── seed-data.py            # Demo data generator
│       └── init-db.sh
├── docs/
│   ├── SPEC.md                     # This document
│   ├── API.md                      # Auto-generated from OpenAPI
│   ├── DEPLOYMENT.md
│   ├── USER_GUIDE.md
│   └── WHITELABEL.md
└── README.md
```

---

## 3. Data Model (Core Entities)

### 3.1 Organizations (Multi-Tenant)

```
Organization {
  id: UUID (PK)
  name: string
  slug: string (unique, for subdomain)
  logo_url: string?
  timezone: string (default: America/Nassau)
  currency: string (default: USD)
  country: string (default: BS)
  regs: string[] (['FAR-135', 'OTAR', 'EASA', ...])
  is_active: boolean
  settings: JSONB (feature flags, config)
  created_at: datetime
  updated_at: datetime
}
```

### 3.2 Users & Roles (RBAC)

> **All major entities (Aircraft, Flight, MaintenanceTask, CrewMember, Document, FinancialRecord)
> are scoped to organization_id. Every query enforces org isolation at the service layer
> — never at the application level. This is non-negotiable for multi-tenant safety.**

```
User {
  id: UUID (PK)
  organization_id: UUID (FK)
  email: string (unique within org)
  password_hash: string
  display_name: string
  phone: string?
  role: enum('super_admin', 'ops_manager', 'admin', 'pilot', 'mechanic', 'readonly')
  is_active: boolean
  mfa_enabled: boolean
  mfa_secret: string? (encrypted)
  last_login: datetime?
  created_at: datetime
}

Role Hierarchy:
  super_admin  → full access, manage org, billing
  ops_manager  → all ops features, manage crew/aircraft/finance
  admin        → scheduling, documents, compliance
  pilot        → view assignments, log flights, view own records
  mechanic     → view/maintain maintenance records, log work
  readonly     → dashboard viewing only
```

### 3.3 Aircraft (Fleet)

```
Aircraft {
  id: UUID (PK)
  organization_id: UUID (FK)
  tail_number: string (e.g. "C6-PRD")
  serial_number: string?
  make: string (e.g. "Cessna")
  model: string (e.g. "208B Grand Caravan")
  year: integer
  category: enum('piston', 'turboprop', 'light_jet', 'midsize_jet', 'heavy_jet', 'helicopter')
  mtow_kg: float?
  max_seats: integer
  max_cargo_kg: float?
  engines: integer (1 or 2)
  engine_type: enum('piston', 'turboprop', 'turbofan')
  current_cycles: integer (airframe)
  current_hours: float (airframe, hobbs)
  status: enum('active', 'maintenance', 'grounded', 'ferry', 'retired')
  base: string (airport code, e.g. "MYNN")
  home_airport: string
  country_reg: string (e.g. "BS" or "N" for Bahamas)
  registration_expiry: date?
  insurance_policy: string?
  insurance_expiry: date?
  notes: text?
  metadata: JSONB (flexible fields per type)
  created_at: datetime
  updated_at: datetime
}
```

### 3.4 Aircraft Components

```
AircraftComponent {
  id: UUID (PK)
  aircraft_id: UUID (FK)
  name: string (e.g. "Engine #1 - PT6A-114A")
  part_number: string?
  serial_number: string?
  position: enum('left', 'right', 'apu', 'n/a')
  component_type: enum('engine', 'propeller', 'landing_gear', 'avionics', 'battery', 'life_vest', 'fire_bottle', 'other')
  installed_date: date
  installed_hours: float (airframe hours at install)
  installed_cycles: integer (airframe cycles at install)
  tbo_hours: float? (Time Before Overhaul)
  tbo_cycles: integer?
  tbo_calendar_days: integer? (e.g. 3650 for 10-year items)
  life_limited: boolean
  status: enum('serviceable', 'overhaul_due', 'expired', 'removed')
  notes: text?
}
```

### 3.5 Maintenance Tasks

```
MaintenanceTask {
  id: UUID (PK)
  aircraft_id: UUID (FK)
  component_id: UUID? (FK, nullable for airframe-level tasks)
  title: string
  description: text?
  task_type: enum('inspection', 'oil_change', 'ad', 'sb', 'overhaul', 'repair', 'annual', '100hr', 'phase')
  reference: string? (e.g. "AD 2023-08-15", "Cessna SB 208-123")
  interval_type: enum('hours', 'cycles', 'calendar', 'event')
  interval_value: float? (e.g. 100 hours)
  interval_unit: string? (e.g. "hours", "cycles", "days")
  recurring: boolean
  requires_faa8130: boolean        # Parts requiring 8130 tag
  requires_maintenance_release: boolean  # FAR 135 requirement
  status: enum('scheduled', 'overdue', 'in_progress', 'completed', 'deferred')
  assigned_to: UUID? (FK -> user)
  scheduled_date: date?
  completed_date: datetime?
  completed_hours: float?
  completed_cycles: integer?
  approved_by: UUID? (FK -> user)
  deferral_ref: string? (MEL item #, approval doc)
  created_by: UUID (FK -> user)
  created_at: datetime
  updated_at: datetime
}
```

### 3.6 Flights

```
Flight {
  id: UUID (PK)
  organization_id: UUID (FK)
  aircraft_id: UUID (FK)
  flight_number: string? (internal)
  tail_number: string (denormalized for quick ref)
  type: enum('passenger', 'cargo', 'ferry', 'positioning', 'training', 'charter')
  status: enum('scheduled', 'active', 'completed', 'cancelled', 'diverted')
  departure_airport: string (ICAO)
  arrival_airport: string (ICAO)
  alternate_airport: string? (ICAO)
  departure_time: datetime? (scheduled)
  arrival_time: datetime? (scheduled)
  actual_departure: datetime? (actual)
  actual_arrival: datetime? (actual)
  flight_time_hours: float? (hobbs)
  cycles: integer? (usually 1 per leg)
  fuel_burned_liters: float?
  fuel_cost: decimal?
  pilot_in_command: UUID? (FK -> crew)
  second_in_command: UUID? (FK -> crew)
  crew_members: UUID[] (other crew)
  passengers_count: integer?
  cargo_weight_kg: float?
  customs_clearance_ref: string?
  manifest_ref: string?
  revenue: decimal?
  notes: text?
  created_at: datetime
  updated_at: datetime
}
```

### 3.7 Crew Members

```
CrewMember {
  id: UUID (PK)
  organization_id: UUID (FK)
  user_id: UUID? (FK, nullable for non-user crew)
  first_name: string
  last_name: string
  email: string?
  phone: string?
  role: enum('captain', 'first_officer', 'sic', 'mechanic', 'flight_attendant', 'dispatcher')
  license_type: enum('atpl', 'cpl', 'ppl', 'mechanics')
  license_number: string?
  license_country: string
  license_expiry: date?
  medical_class: enum(1, 2, 3)
  medical_expiry: date?
  passport_number: string?
  passport_expiry: date?
  visa_details: JSONB? (country, expiry)
  date_of_hire: date
  status: enum('active', 'onleave', 'training', 'sick', 'inactive', 'terminated')
  base_airport: string
  currency_metrics: JSONB {
    last_90d_hours: float,
    last_90d_landings: integer,
    last_12m_hours: float,
    current_duty_day_hours: float,
    duty_period_end: datetime?,
    last_flight: datetime?,
    last_proficiency: datetime?,
    last_medical: datetime?,
  }
  created_at: datetime
  updated_at: datetime
}
```

### 3.8 Crew Qualifications & Training

```
CrewQualification {
  id: UUID (PK)
  crew_id: UUID (FK)
  aircraft_id: UUID? (FK, type-specific if applicable)
  qual_type: enum('type_rating', 'proficiency_check', 'line_check', 'instrument_rating',
                   'recurrent_training', 'differential_training', 'hazmat', 'dgr', 'first_aid')
  status: enum('current', 'expiring_soon', 'expired')
  issued_date: date
  expiry_date: date?
  completed_hours: float?
  notes: string?
  created_at: datetime
}
```

### 3.9 Documents & Compliance

```
Document {
  id: UUID (PK)
  organization_id: UUID (FK)
  aircraft_id: UUID? (FK)
  crew_id: UUID? (FK)
  title: string
  doc_type: enum('airworthiness_cert', 'registration', 'insurance', 'operating_specs',
                  'opus_specs', 'caribbean_waiver', 'customs_clearance', 'noise_cert',
                  'export_cert', 'dry_lease', 'crew_license', 'medical', 'training_record',
                  'maintenance_manual', 'ops_manual', 'mel', 'other')
  doc_number: string? (reference number)
  issuing_authority: string? (e.g. "BCAA", "FAA", "OTAR")
  issue_date: date
  expiry_date: date?
  reminder_days: integer (default 30)
  file_url: string? (path to uploaded PDF)
  status: enum('current', 'expiring_soon', 'expired', 'revoked')
  notes: text?
  created_at: datetime
  updated_at: datetime
}
```

### 3.10 Financial Records

```
FinancialRecord {
  id: UUID (PK)
  organization_id: UUID (FK)
  aircraft_id: UUID (FK)
  flight_id: UUID? (FK)
  record_type: enum('revenue', 'cost', 'invoice', 'expense')
  category: enum('charter_revenue', 'cargo_revenue', 'fuel', 'maintenance',
                  'crew', 'insurance', 'landing_fees', 'handling', 'hangar',
                  'training', 'navigation', 'customs', 'misc')
  amount: decimal
  currency: string (default: USD)
  description: string?
  entry_date: date
  reference: string? (invoice #, receipt #)
  tax_applicable: boolean
  created_at: datetime
}
```

### 3.11 Audit Log

```
AuditLog {
  id: UUID (PK)
  organization_id: UUID
  user_id: UUID? (null for system actions)
  action: string (e.g. "flight.created", "maintenance.completed", "user.role_changed")
  entity_type: string (e.g. "flight", "aircraft")
  entity_id: UUID
  old_values: JSONB?
  new_values: JSONB?
  ip_address: string?
  user_agent: string?
  created_at: datetime
}
```

---

## 4. Module Specifications (MVP First)

### Module 1: Auth & Organization Setup
**Priority: P0 | Effort: 3 days | Dependencies: None**

- Email/password registration + login
- JWT access + refresh tokens
- MFA via TOTP (optional per user)
- Role-based access control (RBAC) middleware
- Organization creation wizard (multi-tenant)
- Invite users via email link
- Password reset flow
- Session management (active sessions, force logout)
- Audit log for all auth events

### Module 2: Fleet Configuration
**Priority: P0 | Effort: 2 days | Dependencies: Module 1**

- Add/edit/retire aircraft
- Aircraft detail page with all config
- Component tracking (engines, props, LEs, etc.)
- Bulk aircraft import from CSV
- Status badges (active/maintenance/grounded/ferry)
- Tail number search
- Aircraft image + logo

### Module 3: Maintenance Tracking
**Priority: P0 | Effort: 5 days | Dependencies: Module 2**

- Maintenance task library (recurring + one-time)
- Inspection interval tracking (hours/cycles/calendar)
- AD/SB compliance tracker
- Due/overdue dashboard with color-coded alerts
- Maintenance log entry (with signature)
- Deferred maintenance (MEL) workflow
- 100-hour / Annual / Phase inspection tracking
- Component TBO tracking with alerts
- Parts tracking (with 8130 tag support for FAR 135)
- Maintenance release (FAR 135.65 requirement)
- Calendar integration (Google Calendar / iCal export)
- Email reminders for upcoming tasks

### Module 4: Flight Operations & Scheduling
**Priority: P0 | Effort: 5 days | Dependencies: Module 2, Module 3**

- Flight scheduling calendar (weekly/monthly view)
- Trip creation (route, aircraft, crew, pax, cargo)
- Manifest generation (passenger + cargo)
- Flight log entry (actuals vs scheduled)
- Crew assignment with conflict detection
- Duty time tracking (FAR 135.267/271 compliance)
- Airport database (ICAO codes, coordinates, FBOs)
- Route library (frequent routes)
- Customs / CIQ flagging for international legs
- Real-time status board (scheduled / active / completed / diverted)
- Flight tracking via ADS-B integration (ADSB.lol / OpenSky)
- Automatic manifest + customs form generation

### Module 5: Crew Management
**Priority: P0 | Effort: 3 days | Dependencies: Module 1**

- Crew member profiles (all license/medical/passport data)
- Currency dashboard (90-day, 12-month, duty-day limits)
- Qualification tracking with expiry alerts
- Training records (proficiency checks, recurrent training)
- Crew scheduling (assign to trips)
- Duty time calculator (FAR 117 or 135)
- Crew availability / leave management
- Document expiration reminders (medical, license, passport)

### Module 6: Compliance & Document Management
**Priority: P0 | Effort: 3 days | Dependencies: Module 2, Module 5**

- Document upload + metadata (type, authority, expiry)
- Expiration tracking dashboard (color-coded: green/yellow/red)
- Document storage (S3/Minio local storage)
- Country-specific compliance tags:
  - **Bahamas (BCAA):** operating specs, air operator certificate, noise cert, overflight permits, customs pre-clearance, landing permits, passenger manifests
  - **Haiti:** MTTP landing permits, overflight clearances (PROFODA), cargo customs declarations, passenger visa checks, security clearances
  - **US:** TSA rules, customs pre-clearance, APIS manifest, eAPIS filing
  - **Caribbean island-hopping:** blanket overflight waivers, multi-stop customs protocols
- Compliance checklist per route (auto-calculated — "Before flying MYNN→MTPP you need: BCAA AOC, Haiti overflight permit, customs pre-clearance, passenger manifest")
- Export/audit report (PDF)
- Automated reminder emails (configurable lead time per doc type)
- Version history for documents
- BCAA-specific fields: AOC number, AOC expiry, OpSpec reference, inter-carrier agreement references

### Module 7: Financial Dashboard
**Priority: P0 | Effort: 4 days | Dependencies: Module 2, Module 4**

- **Auto-record creation** — completing a flight or maintenance event automatically creates financial records:
  - Flight completed → auto-generates revenue entry (charter/cargo rate) + cost entries (fuel burn × price, crew hourly, landing fees)
  - Maintenance completed → auto-generates cost entry (parts + labor, reference to invoice)
  - Manual override always available for adjustments
- P&L per tail number (auto-calculated per flight)
- Cost categories: fuel, crew, maintenance, landing/handling, insurance, misc
- Revenue tracking per flight/charter
- Monthly/quarterly/YTD financial summaries
- Profit margin per route
- Budget vs actual tracking
- QuickBooks export (CSV/QBO format)
- Invoice generation (basic)
- Fuel cost tracking (gallons, price per gallon)
- Break-even analysis per aircraft

### Module 8: Operation Center Dashboard
**Priority: P0 | Effort: 3 days | Dependencies: All above (at minimum Modules 1-4)**

- Single-pane view of today's operations
- Aircraft status widget (each tail — color-coded card with live position on MapLibre GL map)
- **ADS-B live tracking** — each aircraft shown as moving icon on map, click for flight details (speed, altitude, heading, last seen). Data from ADSB.lol / OpenSky API, updated via WebSocket polling (15s interval)
- Upcoming maintenance alerts
- Today's flight schedule (timeline view)
- Crew duty status
- Weather at bases (Open-Meteo API)
- Recent financial snapshot
- Quick actions (log flight, add maintenance, create trip)
- Notification bell (pending tasks, approvals, expirations)
- Real-time last-seen timestamps for fleet

### Module 9: Comms & Emergency Alerting
**Priority: P0 (Phase 1) | Effort: 2 days | Dependencies: Module 1**

- **WebSocket notification bus** — real-time push to all connected clients (maintenance due, flight status changes, expiry alerts)
- **Emergency alert button** — prominent on Operation Center and mobile PWA:
  - One tap triggers: dashboard-wide red banner, email to ops team, SMS via Twilio/email-to-SMS gateway
  - Configurable escalation: who gets notified, by what channel, at what severity
- Notification preferences per user (email, SMS, in-app, push)
- Unacknowledged alert escalation (if not dismissed in N minutes, escalate up the chain)
- Alert history log (timestamped, acknowledged by whom, resolution notes)
- Integration with external notification channels (Twilio for SMS, SendGrid/Resend for email)

### Module 10: Onboarding Wizard
**Priority: P1 (Phase 1) | Effort: 2 days | Dependencies: Module 1**

- Step-by-step setup wizard for new organization
- Add first aircraft
- Add first crew members
- Configure maintenance intervals
- Set up basic financial accounts
- Upload compliance documents
- "Quick Start" mode with demo data
- Help tooltips throughout

### Module 11: AI Help Desk (Stub)
**Priority: P1 (Phase 1) | Effort: 1 day | Dependencies: Module 1**

- In-app chat interface (modal, collapsible)
- Context-aware queries via integrated Hermes agent:
  - "When was the last oil change on C6-PRD?" → checks maintenance records
  - "What docs do I need for Nassau to Haiti?" → checks route compliance
  - "What maintenance is due in the next 30 days?" → forecasts from task intervals
- Pre-built Q&A templates for common ops questions
- Extensible: additional Hermes plug-in skills added per operator's needs

### Module 12: White-Label / Multi-Tenant
**Priority: P1 (Phase 2) | Effort: 3 days | Dependencies: Module 1**

- Organization branding (logo, colors, favicon)
- Custom subdomain (acme.ops.pararig.com)
- Custom email templates
- Feature flags per tenant
- Usage/billing tier management
- Self-hosted license key generation

---

## 5. API Design Principles

- **RESTful** — resources as nouns, HTTP verbs as actions
- **Versioned** — `/api/v1/aircraft`
- **Consistent** — pagination via `?page=1&per_page=25`, sorting via `?sort=-created_at`
- **OpenAPI** — auto-generated docs at `/docs` and `/redoc`
- **Response envelope:**
```json
{
  "data": { ... },
  "meta": { "page": 1, "per_page": 25, "total": 142 },
  "error": null
}
```

### Key Endpoints (MVP)

```
POST   /api/v1/auth/login
POST   /api/v1/auth/register
GET    /api/v1/auth/me
POST   /api/v1/auth/mfa/setup
POST   /api/v1/auth/mfa/verify

GET    /api/v1/aircraft
POST   /api/v1/aircraft
GET    /api/v1/aircraft/{id}
PATCH  /api/v1/aircraft/{id}
DELETE /api/v1/aircraft/{id}
GET    /api/v1/aircraft/{id}/components
GET    /api/v1/aircraft/{id}/maintenance
GET    /api/v1/aircraft/{id}/flights
GET    /api/v1/aircraft/{id}/financial

GET    /api/v1/maintenance
POST   /api/v1/maintenance
GET    /api/v1/maintenance/{id}
PATCH  /api/v1/maintenance/{id}
GET    /api/v1/maintenance/due
GET    /api/v1/maintenance/overdue
GET    /api/v1/maintenance/search?q=AD+2023

GET    /api/v1/flights
POST   /api/v1/flights
GET    /api/v1/flights/{id}
PATCH  /api/v1/flights/{id}
GET    /api/v1/flights/active
GET    /api/v1/flights/calendar?from=...&to=...

GET    /api/v1/crew
POST   /api/v1/crew
GET    /api/v1/crew/{id}
PATCH  /api/v1/crew/{id}
GET    /api/v1/crew/{id}/qualifications
GET    /api/v1/crew/available?aircraft_id=...&date=...

GET    /api/v1/compliance/documents
POST   /api/v1/compliance/documents
GET    /api/v1/compliance/documents/{id}
GET    /api/v1/compliance/expiring
GET    /api/v1/compliance/checklist?from=...&to=...

GET    /api/v1/finance/pnl?tail=...&from=...&to=...
GET    /api/v1/finance/costs?tail=...
GET    /api/v1/finance/summary?period=monthly|quarterly|yearly

GET    /api/v1/dashboard/today
GET    /api/v1/dashboard/alerts
GET    /api/v1/dashboard/maintenance-forecast
GET    /api/v1/dashboard/financial-snapshot

GET    /api/v1/airports?search=...
GET    /api/v1/routes
POST   /api/v1/routes

GET    /api/v1/admin/users
POST   /api/v1/admin/invite
PATCH  /api/v1/admin/users/{id}/role
```

---

## 6. UI/UX Design Language

### Design System
- **Panel** — shadcn/ui components (consistent, accessible)
- **Dark mode first** — aviation ops centers run dark, respect that
- **Mobile-first responsive** — pilots enter data on phones
- **PWA offline cache** — cached routes, maintenance schedules, and flight lists available without connectivity

### Key Screens (MVP)

**Operation Center (Home)**
```
┌─────────────────────────────────────────────────────┐
│ HEADER:  Logo | Today's Date | Weather: 82°F / 28°C│
│                 MYNN: VFR 10sm | MTPP: VFR 8sm      │
│         [Log Flight] [Add Mx] [Create Trip]         │
├───────────────────┬─────────────────────────────────┤
│ Aircraft Status   │ Today's Schedule                │
│ ┌───────────────┐ │ ┌─────────────────────────────┐ │
│ │ C6-PRD  ACTIVE│ │ │ 0800 C6-PRD → MTPP (Capt J) │ │
│ │ Hobbs: 4523hr │ │ │ 1000 C6-PRV → MYGF (FO W)   │ │
│ │ D Update: 12hr│ │ │ 1400 C6-PRD → MYNN (Capt J) │ │
│ └───────────────┘ │ └─────────────────────────────┘ │
│ ┌───────────────┐ │ Alerts                          │
│ │ C6-PRV  IN MX │ │ ⚠ 100hr due C6-PRD in 23hrs   │
│ │ Due: Oil Chng │ │ 🔴 Medical expiring: S. Jones  │
│ └───────────────┘ │ 🟡 Insurance renew Aug 15      │
├───────────────────┴─────────────────────────────────┤
│ Quick P&L: Month-to-Date                            │
│ C6-PRD: +$12,400 | C6-PRV: -$3,200 (in mx)        │
│ Fleet Total: +$9,200                                │
└─────────────────────────────────────────────────────┘
```

**Fleet Dashboard**
- Grid of aircraft cards with color-coded status
- Each card: tail number, type, status badge, next maintenance, last flight, hours/cycles
- Click through to aircraft detail

**Aircraft Detail**
- Tabs: Overview | Maintenance | Flights | Components | Documents | Financial
- Overview: all config fields, status, current location on map
- Maintenance tab: timeline of tasks, due/overdue counter
- Flights tab: sortable/searchable history

**Maintenance View**
- Calendar-style view of upcoming inspections
- Filterable by tail, type, status
- Due/overdue counts with red/orange/green badges
- Click-to-complete workflow with digital signature

**Flight Schedule**
- Weekly calendar view (drag to create trip)
- Gantt-style timeline for day-of ops
- Crew assignment with parallel flight conflict detection
- Manifest popup per trip

---

## 7. Security

### Auth & Access
- bcrypt password hashing (work factor 12)
- JWT access tokens (15min TTL) + refresh tokens (7 day TTL, rotate on use)
- MFA via time-based OTP (TOTP) — authenticator app
- Rate limiting on auth endpoints (5 attempts/15min per IP)
- Session invalidation on password change
- RBAC enforced at router level + service layer

### API Security
- CORS restricted to frontend origin
- All requests logged (who, what, when, IP)
- SQLAlchemy parameterization — no raw SQL by convention
- File upload validation (MIME type, size cap: 25MB)
- API key support for programmatic access (optional)

### Data Security
- All passwords hashed, never stored plaintext
- MFA secrets encrypted at rest (AES-256)
- S3/Minio storage with signed URLs for document access
- Database backups encrypted
- Audit trail immutable (append-only pattern)

### Infrastructure
- Caddy auto-TLS for HTTPS
- Docker secrets for sensitive env vars
- UFW on host: only SSH + Docker bridge open
- Tailscale recommended for admin access
- `Content-Security-Policy` headers on all responses
- Helmet.js (or equivalent) middleware

---

## 8. Deployment

### Docker Compose (Self-Hosted)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: pararig_ops
      POSTGRES_USER: pararig
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  backend:
    build: ./backend
    env_file: .env
    depends_on: [postgres]
    volumes: [uploads:/app/uploads, static:/app/static]

  frontend:
    build: ./frontend
    env_file: .env
    depends_on: [backend]

  caddy:
    image: caddy:2-alpine
    ports: [80:80, 443:443]
    volumes: [./Caddyfile:/etc/caddy/Caddyfile, caddy_data:/data]
```

### Environment Variables

```
# Database
DATABASE_URL=postgresql+asyncpg://pararig:${DB_PASSWORD}@postgres:5432/pararig_ops
SQLITE_URL=sqlite+aiosqlite:///./pararig_ops.db

# Auth
SECRET_KEY=<random-64-char-hex>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# MFA
MFA_ENCRYPTION_KEY=<random-32-char>

# Storage
UPLOAD_DIR=/app/uploads
S3_ENDPOINT=  # optional, use local by default
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=

# External APIs
ADSB_API_KEY=
OPENSKY_USERNAME=
OPENSKY_PASSWORD=
WEATHER_API_KEY=

# Stripe (SaaS mode)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Email (notifications)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
FROM_EMAIL=ops@pararig.com

# Instance
INSTANCE_MODE=self_hosted|saas
LICENSE_KEY=  # for self-hosted activation
```

### First-Run Walkthrough

1. `cp .env.example .env && vim .env` — set secrets
2. `docker compose up -d` — launches DB, backend, frontend, Caddy
3. Backend auto-runs Alembic migrations on startup
4. Visit `https://ops.pararig.com` — registration page
5. First user to register becomes org super_admin
6. Onboarding wizard steps through initial configuration
7. Seed demo data available for evaluation

---

## 9. Phased Development Roadmap

### Phase 1 — MVP + Comms (5-7 weeks)

**We build in dependency order. Each module is demo-able before starting the next.**

| # | Module | Weeks | Depends On |
|---|--------|-------|-----------|
| 1 | Auth + Org + RBAC | 1 | None |
| 2 | Fleet Configuration | 3 days | Module 1 |
| 3 | Maintenance Tracking | 1.5 | Module 2 |
| 4 | Flight Ops & Scheduling | 1.5 | Modules 2, 3 |
| 5 | Crew Management | 1 | Module 1 |
| 6 | Compliance & Docs (BCAA/Haiti/US) | 1 | Modules 2, 5 |
| 7 | Financial Dashboard (auto-record) | 1 | Modules 2, 4 |
| 8 | Operation Center (with ADS-B map) | 3 days | All above |
| 9 | Comms & Emergency Alerting | 2 days | Module 1 |
| 10 | Onboarding Wizard | 2 days | Module 1 |
| 11 | AI Help Desk (stub) | 1 day | Module 1 |

**Deliverable:** A full-stack system you can use day one for your 2-aircraft Nassau ↔ Haiti operation. Manage aircraft, schedule flights, log maintenance, track crew currency, handle BCAA/Haiti compliance, see real-time P&L, and get alerted on emergencies — all from a modern dark-mode dashboard with ADS-B tracking on a live map.

### Phase 2 — Production Hardening (2-3 weeks)
- PWA offline mode (service worker, cached routes)
- Email notifications (SendGrid/Resend)
- QuickBooks sync (API integration)
- PDF manifest/invoice generation
- Multi-base support
- audit log viewer in-app
- Performance optimization

### Phase 3 — Advanced (ongoing)
- AI Help Desk full deployment (deep Hermes integration)
- White-label + multi-tenant billing
- SaaS billing (Stripe)
- Advanced analytics & forecasting
- SATCOM / iridium comms integration
- Custom reporting engine

---

## 10. Development Standards

### Python / Backend
- Type hints everywhere — `mypy --strict` compliant
- Async endpoints (FastAPI async handlers)
- Repository pattern for data access (services don't touch SQLAlchemy directly)
- Pydantic v2 for all schemas
- Unit tests with `pytest` + `httpx.AsyncClient`
- Coverage target: 80%+
- Black + Ruff for formatting/linting

### TypeScript / Frontend
- Strict mode TypeScript
- React Query for all server state
- Zustand for client-only state (ui state, form drafts)
- React Router v7 for routing
- Vitest + Testing Library for tests
- Prettier + ESLint

### Database
- Alembic for migrations (always `down_revision` exists for rollback)
- All timestamps UTC
- Soft deletes where possible (`deleted_at` column)
- Indexes on all foreign keys + commonly queried columns
- JSONB for flexible metadata (not EAV pattern)
- Use ENUM types for bounded values (not magic strings)

### Git
- Branch: `main` (stable), `develop` (active), feature branches
- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`
- PRs require at minimum your own review before merge
- Sqash-merge feature branches into develop

---

## 11. Dependencies & Integrations

### MVP Required
- **PostgreSQL 16** — primary database
- **Minio / local filesystem** — document storage (swap to S3 later)
- **Open-Meteo** — free weather API (no API key)
- **OpenStreetMap / MapLibre** — free maps

### Phase 2
- **ADSB.lol** — free ADS-B feed (no API key needed for basic)
- **OpenSky Network** — additional ADS-B data
- **Resend / SendGrid** — transactional email
- **Stripe** — SaaS payments

### Phase 3
- **QuickBooks API** — accounting sync
- **ICAO API** — airport database
- **Your own dump1090** — if you run an ADS-B receiver

---

## 12. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| SQLite won't support concurrent writes | Medium | Low | Use PostgreSQL in production, SQLite only for single-user dev |
| React PWA is overkill for MVP | Medium | Low | Start with shadcn/ui + SSR, add PWA shell later |
| ADS-B integration is complex | Medium | Medium | Use ADSB.lol API (free, simple) — no dump1090 required |
| Multi-tenant data isolation bug | Low | High | Each query scoped to `organization_id` — enforce at middleware level |
| Offline sync is hard | High | Medium | Postpone full offline to Phase 2; use simple cached reads in MVP |
| Regulatory compliance varies by country | Medium | Medium | Flexible document tagging system — don't hardcode any country logic |

---

## 13. Next Steps

1. **You review this spec** — flag anything I got wrong, anything missing, anything you'd change
2. **Grok reviews from your side** — domain validation, architecture feedback
3. **We lock the spec** — sign off on the MVP scope
4. **I scaffold the project** — backend skeleton, DB schema, Alembic migrations, Docker setup
5. **Module 1 (Auth)** — full build-out, demo-able
6. **Continue module-by-module** per the roadmap above
7. **You test against real ops** — you're the domain expert, you validate

---

*"The only way to fly a complex operation is with a system that makes complexity invisible."*
