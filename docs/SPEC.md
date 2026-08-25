# ParaRig Aviation Operations Suite — Full Specification

**Project:** Aviation Operations Management System (Ops VP)
**Client:** ParaRig Dynamics / Private Aviation Operation (Nassau ↔ Haiti)
**Version:** 2.0 — Built & Operational
**Date:** 2026-07-24
**Author:** Hermes (The Citadel) + Grok + Shawn

---

## 1. Vision Statement

A white-label, turnkey aviation management suite that feels modern and intuitive — not like the legacy ERP systems that dominate this space (AvPro, FlightDocs, etc.). Unifies maintenance scheduling, flight operations, crew management, compliance, and financial tracking into a single pane of glass.

**Core philosophy:** A pilot should be able to log their flight, a mechanic should see the inspection due, the Ops VP should see the P&L, and the compliance officer should see the upcoming renewal — all from the same system, in real time, without spreadsheets or sticky notes.

**Current status:** All Phase 1 modules are **built and operational**. The system is running on SQLite (dev) with production readiness for PostgreSQL. The spec has been signed off; the focus has shifted to hardening, testing, and polish.

---

## 2. Architecture Overview

### 2.1 Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Backend** | FastAPI (Python 3.12+) | Async, auto-OpenAPI, fast to build, easy to audit |
| **Database** | PostgreSQL 16 (production) / SQLite (dev/demo fallback) | SQLite for single-user dev, PG for production multi-user |
| **ORM** | SQLAlchemy 2.0 + Alembic | Mature, async-ready, migration-driven schema |
| **Frontend** | React 18 + TypeScript + Tailwind CSS 4 | PWA-capable, mobile-first, modern UX |
| **State / Data** | TanStack React Query | Server-state caching |
| **UI Components** | shadcn/ui + Radix Primitives | Accessible, composable, Tailwind-native |
| **Maps** | MapLibre GL (open-source) | Self-hosted tile server option, no Google dependency |
| **Auth** | JWT (python-jose) + bcrypt + MFA (TOTP via pyotp) | Battle-tested, extendable |
| **Container** | Docker + docker-compose | Single `docker compose up` to deploy |
| **Reverse Proxy** | Caddy (auto-TLS) | Simpler than nginx + certbot, built-in Let's Encrypt |
| **Fleet Tracking** | ADSB.lol / OpenSky API | WebSocket-based aircraft position feed |
| **Weather** | AviationWeather.gov (NOAA/FAA ADDS) | Free, no API key, real aviation METAR/TAF |
| **NOTAMs** | FAA NMS API (OAuth2) | Free with registration, production FAA NOTAM data |

### 2.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Caddy (TLS Proxy)                  │
│              *.opspanel.local / ops.pararig.com      │
├──────────────────────┬──────────────────────────────┤
│      Frontend        │         Backend API            │
│   React + Tailwind   │    FastAPI + SQLAlchemy        │
│   Vite (build)       │    uvicorn (serve)             │
├──────────────────────┴──────────────────────────────┤
│                 PostgreSQL 16                         │
│    (or SQLite for single-user / dev mode)             │
├─────────────────────────────────────────────────────┤
│   File Storage (local / S3/Minio)                    │
│   (docs, logsheets, manifests)                       │
└─────────────────────────────────────────────────────┘
```

### 2.3 Data Flow Principles

1. **Every flight generates a financial record** — auto-calculated cost vs revenue by tail number
2. **Every maintenance event generates a log entry** — timestamped, user-attributed
3. **Every document has a reminder** — expiration tracking with configurable lead time
4. **Every crew member has a currency dashboard** — hours, medicals, training, quals at a glance
5. **All changes are audited** — immutable audit log with who-did-what-when

### 2.4 Directory Structure (Actual)

```
pararig-ops/
├── backend/
│   ├── app/
│   │   ├── api/                    # Route handlers
│   │   │   ├── v1/                 # 31 route files
│   │   │   │   ├── auth.py                    # Login, register, MFA, token refresh
│   │   │   │   ├── aircraft.py                # Aircraft CRUD + components
│   │   │   │   ├── airports.py                # Airport database lookup (OurAirports)
│   │   │   │   ├── routes.py                  # Route library + route planner
│   │   │   │   ├── maintenance.py             # Maintenance tasks CRUD
│   │   │   │   ├── maintenance_dashboard.py   # Maintenance dashboard (due/overdue)
│   │   │   │   ├── flights.py                 # Flight CRUD
│   │   │   │   ├── flight_releases.py         # Part 135 flight release (3-gate signoff)
│   │   │   │   ├── crew.py                    # Crew member CRUD + qualifications
│   │   │   │   ├── compliance.py              # Document upload, expiry tracking
│   │   │   │   ├── comms.py                   # WebSocket notification bus
│   │   │   │   ├── finance.py                 # P&L, financial records
│   │   │   │   ├── tracking.py                # ADS-B live tracking
│   │   │   │   ├── ops_checks.py              # Operational checklists
│   │   │   │   ├── missions.py                # Multi-leg mission planning
│   │   │   │   ├── passengers.py              # Passenger management
│   │   │   │   ├── users.py                   # User management
│   │   │   │   ├── org_settings.py            # Organization settings
│   │   │   │   ├── admin.py                   # Admin endpoints (invite, bootstrap)
│   │   │   │   ├── bulk_import.py             # CSV bulk import
│   │   │   │   ├── export.py                  # Data export
│   │   │   │   ├── logbook.py                 # Pilot logbook
│   │   │   │   ├── reports.py                 # Reporting endpoints
│   │   │   │   ├── weather_router.py          # Weather / METAR / TAF / NOTAM
│   │   │   │   ├── costs.py                   # Cost tracking
│   │   │   │   ├── leg_costs.py               # Per-leg cost logging
│   │   │   │   ├── briefing.py                # Mission briefing
│   │   │   │   ├── permissions.py             # Permission introspection
│   │   │   │   ├── onboarding.py              # Onboarding wizard
│   │   │   │   └── helpdesk.py                # AI help desk (chat interface)
│   │   │   └── deps.py                        # Dependency injection (get_db, etc.)
│   │   ├── core/
│   │   │   ├── config.py           # Settings from env (Pydantic Settings)
│   │   │   ├── database.py         # SQLAlchemy engine + session + init_db
│   │   │   ├── security.py         # JWT, MFA, password hashing
│   │   │   ├── audit.py            # Audit log middleware
│   │   │   ├── permissions.py      # RBAC dependency (require_role, require_feature)
│   │   │   ├── roles.py            # 11-role FAA Part 135 enum + hierarchy
│   │   │   └── features.py         # 26-feature permission matrix + resolver
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── aircraft.py         # Aircraft + AircraftComponent
│   │   │   ├── airport.py          # Airport database (OurAirports data)
│   │   │   ├── audit.py            # AuditLog
│   │   │   ├── crew.py             # CrewMember + CrewQualification
│   │   │   ├── document.py         # Document (compliance docs)
│   │   │   ├── finance.py          # FinancialRecord
│   │   │   ├── flight.py           # Flight + Route
│   │   │   ├── flight_release.py   # FlightRelease (Part 135 release doc)
│   │   │   ├── invite.py           # InviteCode
│   │   │   ├── leg_cost.py         # LegCost (per-leg expenses)
│   │   │   ├── logbook.py          # LogbookEntry
│   │   │   ├── maintenance.py      # MaintenanceTask
│   │   │   ├── mission.py          # Mission, FlightLeg, ManifestEntry
│   │   │   ├── notification.py     # Notification
│   │   │   ├── organization.py     # Organization (multi-tenant)
│   │   │   ├── passenger.py        # Passenger
│   │   │   └── user.py             # User (with role, MFA, feature_overrides)
│   │   ├── schemas/                # Pydantic models (request/response)
│   │   │   ├── aircraft.py
│   │   │   ├── airport.py
│   │   │   ├── costs.py
│   │   │   ├── crew.py
│   │   │   ├── document.py
│   │   │   ├── flight.py
│   │   │   ├── leg_costs.py
│   │   │   ├── maintenance.py
│   │   │   ├── mfa.py
│   │   │   ├── mission.py
│   │   │   └── passenger.py
│   │   └── services/               # Business logic layer
│   │       ├── ad_compliance.py    # AD/SB compliance tracker (real ADs for King Air, DHC-6, Basler BT-67)
│   │       ├── airport_lookup.py   # OurAirports data import + search
│   │       ├── crew_duty.py        # FAR 135.267/135.271 duty time calculator
│   │       ├── distance.py         # Haversine distance calculation
│   │       ├── flight_performance.py  # Block time, fuel burn, capabilities check
│   │       ├── route_planner.py    # Mission planning integration layer (W&B, crew, weather, NOTAMs)
│   │       ├── weather.py          # AviationWeather.gov METAR/TAF + FAA NMS NOTAMs
│   │       └── weight_balance.py   # Per-leg weight & balance analysis
│   ├── alembic/                    # Database migrations (7+ migration files)
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_auth.py
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                    # Route pages + layout
│   │   │   ├── layout/            # RootLayout, Sidebar, TopBar
│   │   │   └── pages/             # 20+ page components
│   │   ├── components/ui/          # Shared UI (shadcn/ui primitives)
│   │   ├── features/
│   │   │   ├── auth/              # AuthContext, AuthGuard, useAuth
│   │   │   ├── costs/             # Cost logging form + P&L section
│   │   │   ├── helpdesk/          # AI Help Desk chat panel
│   │   │   ├── map/               # RouteMap component
│   │   │   ├── onboarding/        # Onboarding wizard
│   │   │   └── tracking/          # LiveTrackingMap (ADS-B)
│   │   ├── lib/                   # API client, utilities
│   │   └── types/                 # TypeScript types
│   ├── public/                    # PWA assets
│   ├── tailwind.config.ts
│   ├── vite.config.ts
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── deploy/
│   ├── docker-compose.yml
│   ├── Caddyfile
│   ├── .env.example
│   └── scripts/
│       ├── seed-data.py            # Demo data generator
│       ├── seed-comprehensive-demo.py  # Full demo with aircraft, missions, crew
│       ├── seed-foundation.py       # Foundation seed data
│       ├── seed-for-user.py         # Per-user seed
│       ├── seed-test-scenario.py    # Test scenario seed
│       └── test_caribbean_loop.py   # Caribbean route test
├── docs/
│   ├── SPEC.md                     # This document
│   ├── MULTI_LEG_SCOPE.md          # Multi-leg mission scope
│   ├── SCOPE_FlightRelease.md      # Flight release scope
│   └── SEED_Mission_CaribbeanLoop.md  # Caribbean loop seed docs
├── FEATURE_BACKLOG.md              # Collected future feature ideas
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
  is_active: boolean
  settings: JSONB (feature flags, config)
  created_at: datetime
  updated_at: datetime
}
```

### 3.2 Users & Roles (RBAC — 11-Role FAA Part 135 System)

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
  role: enum(
    'accountable_executive',      # CEO — full access
    'director_of_operations',     # DoO — day-to-day ops authority
    'director_of_safety',         # DoS — safety oversight
    'chief_pilot',                # CP — pilot management
    'director_of_maintenance',    # DOM — maintenance authority
    'vp_finance',                 # VPF — financial read/write
    'ops_manager',                # Ops Manager — operational control
    'dispatcher',                 # DSP — flight releasing
    'pilot',                      # PLT — flight crew, read-only ops
    'maintenance_technician',     # MXT — maintenance write access
    'viewer'                      # VWR — read-only dashboard access
  )
  is_active: boolean
  pii_clearance: boolean          # Can view PII (passenger passport, SSN, etc.)
  mfa_enabled: boolean
  mfa_secret: string? (encrypted)
  feature_overrides: string[]     # Per-user feature grants beyond role
  permissions_version: integer    # Cache-busting for frontend
  last_login: datetime?
  created_at: datetime
  updated_at: datetime
}
```

**Feature Permission System:** The `app/core/features.py` module defines 26 features across 12 categories (aircraft, flights, maintenance, crew, compliance, finance, admin, safety, routes, passengers, reports, comms), mapped into a `FEATURE_PERMISSION_MATRIX` per role. The `User.feature_overrides` JSON field allows granting specific features beyond a user's role level — this is checked by `check_feature_access()` at enforcement time.

**Role Hierarchy:** Each role has a numeric privilege level (20–100). The `Role.hierarchy()` method and `has_privilege()` comparator enable hierarchical role checks (e.g., "at least OPS_MANAGER level").

**Full Permission Matrix (from app/core/roles.py):**

| Resource                | AE  | DoO | DoS | CP  | DOM | VPF | Ops | Dsp | Plt | MxT | Vwr |
|------------------------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| Aircraft: Read         | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  |
| Aircraft: Write        | ✅  | ✅  | ❌  | ✅  | ✅  | ❌  | ✅  | ❌  | ❌  | ❌  | ❌  |
| Aircraft: Delete       | ✅  | ✅  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  |
| Flights: Read          | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ❌  | ✅  |
| Flights: Create        | ✅  | ✅  | ❌  | ✅  | ❌  | ❌  | ✅  | ✅  | ❌  | ❌  | ❌  |
| Maintenance: Read      | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  |
| Maintenance: Write     | ✅  | ✅  | ❌  | ✅  | ✅  | ❌  | ✅  | ❌  | ❌  | ✅  | ❌  |
| Crew: Read             | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ❌  | ✅  |
| Crew: Write            | ✅  | ✅  | ❌  | ✅  | ❌  | ❌  | ✅  | ❌  | ❌  | ❌  | ❌  |
| Compliance: Read       | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ❌  | ❌  | ✅  |
| Compliance: Write      | ✅  | ✅  | ✅  | ❌  | ❌  | ❌  | ✅  | ❌  | ❌  | ❌  | ❌  |
| Finance: Read          | ✅  | ✅  | ✅  | ❌  | ❌  | ✅  | ❌  | ❌  | ❌  | ❌  | ❌  |
| Finance: Write         | ✅  | ✅  | ❌  | ❌  | ❌  | ✅  | ❌  | ❌  | ❌  | ❌  | ❌  |
| Admin: Users           | ✅  | ✅  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  |
| Admin: Settings        | ✅  | ✅  | ✅  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  | ❌  |
| Safety: Read           | ✅  | ✅  | ✅  | ✅  | ✅  | ❌  | ✅  | ❌  | ❌  | ❌  | ❌  |
| Safety: Write          | ✅  | ✅  | ✅  | ❌  | ❌  | ❌  | ✅  | ❌  | ❌  | ❌  | ❌  |

(Additional features: routes:plan, routes:view, passengers:read, passengers:write, pii:access, reports:view, export:data, comms:send, comms:view — matrix continues in `app/core/roles.py`)

### 3.3 Aircraft (Fleet)

```python
# See also: AircraftComponent (sub-assembly tracking)
Aircraft {
  id: UUID (PK)
  organization_id: UUID (FK)
  tail_number: string (e.g. "C6-PRD", unique)
  make: string
  model: string
  year: integer
  serial_number: string (unique)
  category: enum(single_engine_piston, multi_engine_piston, single_engine_turboprop,
                 multi_engine_turboprop, light_jet, midsize_jet, super_midsize_jet,
                 heavy_jet, rotorcraft)
  mtow_kg: decimal?, mlw_kg: decimal?, bhw_kg: decimal?
  max_seats: integer
  max_cargo_kg: decimal?
  fuel_capacity_l: decimal?
  cruise_speed_kt: integer?
  cruise_fuel_flow_gph: decimal?
  climb_speed_kt: integer?, climb_rate_fpm: integer?
  descent_speed_kt: integer?
  taxi_fuel_gallons: decimal? (default 5.0)
  range_nm: integer?, max_range_with_reserves_nm: integer?
  service_ceiling_ft: integer?
  reserve_fuel_minutes: integer? (default 45)
  overwater_capable: boolean
  known_icing_certified: boolean
  rnp_approach_capable: boolean
  rvsm_capable: boolean
  autopilot_type: string? (none/basic/coupled/fms)
  deice_equipped: boolean
  status: enum(active, in_maintenance, grounded, retired, stored)
  base: string (ICAO)
  home_airport: string (ICAO)
  country_reg: string (default: BS)
  registration_expiry: date?
  airworthiness_expiry: date?
  coa_expiry: date?
  insurance_provider: string?
  insurance_policy_number: string?
  insurance_expiry: date?
  insurance_coverage_amount: decimal?
  total_airframe_hours: decimal?
  total_cycles: integer?
  extra_metadata: JSONB
  created_at: datetime
  updated_at: datetime
}
```

### 3.4 Aircraft Components

```
AircraftComponent {
  id: UUID (PK)
  aircraft_id: UUID (FK)
  organization_id: UUID (FK)
  name: string
  part_number: string
  serial_number: string
  position: enum(left, right, nose, tail, center, both, n_a)
  component_type: enum(engine, propeller, landing_gear, battery, avionics, apu, hydraulic, other)
  installed_date: date?
  installed_hours: decimal?
  tbo_hours: decimal?, tbo_cycles: integer?, tbo_calendar_days: integer?
  hours_since_overhaul: decimal?, cycles_since_overhaul: integer?
  life_limited: boolean
  life_limit_hours: decimal?, life_limit_cycles: integer?
  status: enum(serviceable, overhaul_due, overhauled, removed, damaged)
  last_overhaul_date: date?
  notes: text?
  created_at: datetime
  updated_at: datetime
}
```

### 3.5 Maintenance Tasks

```
MaintenanceTask {
  id: UUID (PK)
  organization_id: UUID (FK)
  aircraft_id: UUID (FK)
  title: string
  description: text?
  task_type: enum(inspection, oil_change, ad, sb, overhaul, repair, annual, 100hr, phase)
  status: enum(scheduled, in_progress, completed, overdue, deferred)
  reference: string? (AD/SB reference)
  interval_hours: float?, interval_days: integer?
  scheduled_date: date?
  completed_date: datetime?
  completed_hours: float?, completed_cycles: integer?
  approved_by: string? (user ID)
  notes: text?
  created_at: datetime
  updated_at: datetime
}
```

### 3.6 Flights

```
Flight {
  id: UUID (PK)
  organization_id: UUID (FK)
  aircraft_id: UUID? (FK)
  flight_number: string?
  flight_type: enum(passenger, cargo, ferry, positioning, training, charter)
  status: enum(scheduled, active, completed, cancelled, diverted)
  departure_airport: string (ICAO)
  arrival_airport: string (ICAO)
  alternate_airport: string? (ICAO)
  scheduled_departure: datetime?
  scheduled_arrival: datetime?
  actual_departure: datetime?
  actual_arrival: datetime?
  flight_time_hours: float?
  cycles: integer? (default 1)
  fuel_burned_liters: float?
  pilot_in_command: string? (user ID)
  second_in_command: string? (user ID)
  passengers_count: integer?
  cargo_weight_kg: float?
  customs_clearance_ref: string?
  manifest_ref: string?
  revenue: decimal?
  fuel_cost: decimal?
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
  first_name: string, last_name: string
  email: string?, phone: string?
  role: enum(captain, first_officer, sic, mechanic, flight_attendant, dispatcher)
  license_type: enum(atpl, cpl, ppl, mechanics)
  license_number: string?, license_country: string
  license_expiry: date?
  medical_class: enum(class_1, class_2, class_3)
  medical_expiry: date?
  passport_number: string?, passport_expiry: date?
  visa_details: JSONB?
  date_of_hire: date
  status: enum(active, on_leave, training, sick, inactive, terminated)
  base_airport: string
  currency_metrics: JSONB
  created_at: datetime
  updated_at: datetime
}

CrewQualification {
  id: UUID (PK)
  crew_id: UUID (FK)
  aircraft_id: UUID? (FK)
  qual_type: enum(type_rating, proficiency_check, line_check, instrument_rating,
                   recurrent_training, differential_training, hazmat, dgr, first_aid)
  status: enum(current, expiring_soon, expired)
  issued_date: date
  expiry_date: date?
  completed_hours: float?
  notes: string?
  created_at: datetime
}
```

### 3.8 Documents & Compliance

```
Document {
  id: UUID (PK)
  organization_id: UUID (FK)
  aircraft_id: UUID? (FK), crew_id: UUID? (FK)
  title: string
  doc_type: enum(airworthiness_cert, registration, insurance, operating_specs,
                  opus_specs, caribbean_waiver, customs_clearance, noise_cert,
                  export_cert, dry_lease, crew_license, medical, training_record,
                  maintenance_manual, ops_manual, mel, other)
  doc_number: string?
  issuing_authority: string?
  issue_date: date
  expiry_date: date?
  reminder_days: integer (default 30)
  file_url: string?
  status: enum(current, expiring_soon, expired, revoked)
  notes: text?
  created_at: datetime
  updated_at: datetime
}
```

### 3.9 Financial Records

```
FinancialRecord {
  id: UUID (PK)
  organization_id: UUID (FK)
  aircraft_id: UUID? (FK)
  flight_id: UUID? (FK)
  maintenance_task_id: UUID? (FK)
  record_type: enum(revenue, cost, invoice, expense)
  category: enum(charter_revenue, cargo_revenue, fuel, maintenance, crew,
                  insurance, landing_fees, handling, hangar, training, customs, misc)
  amount: decimal
  currency: string (default: USD)
  description: text?
  entry_date: date
  reference: string?
  created_at: datetime
}
```

### 3.10 Leg Costs (Per-Leg Expenses)

```
LegCost {
  id: UUID (PK)
  flight_leg_id: UUID (FK -> flight_legs)
  category: enum(fuel, handling, landing, customs, parking, misc)
  amount: float
  currency: string (default: USD)
  payment_method: enum(cash, credit, credit_card, wire)
  notes: text?
  receipt_url: text?
  logged_by: string?
  logged_at: datetime
  created_at: datetime
  updated_at: datetime
}
```

### 3.11 Flight Release (Part 135 Document)

```
FlightRelease {
  id: UUID (PK)
  organization_id: UUID (FK)
  release_number: string (unique, auto-generated FR-YYYY-NNN)
  status: enum(draft, released, amended, closed)
  mission_name: string?
  aircraft_id: UUID? (FK)
  origin_icao: string, dest_icao: string, alternate_icao: string?
  departure_time: datetime?
  est_enroute_minutes: integer?
  route_waypoints: JSON (ordered waypoint list)
  pic_id: string?, sic_id: string?
  pic_duty_start: datetime?, pic_duty_end: datetime?
  sic_duty_start: datetime?, sic_duty_end: datetime?
  weather_brief: JSON (per-airport METAR/TAF)
  notam_refs: JSON (NOTAM identifiers)
  ramp_fuel_lbs: float?, trip_fuel_lbs: float?
  contingency_fuel_lbs: float?, alternate_fuel_lbs: float?
  reserve_fuel_lbs: float?, arrival_fuel_lbs: float?
  fuel_legal: boolean
  safe_for_flight: boolean
  maintenance_signed_by: string?, maintenance_signed_at: datetime?
  mission_capability: enum(full, partial, not_capable)
  maintenance_restrictions: JSON?
  gripes_open: JSON, gripes_deferred: JSON
  pic_acceptance: text?
  pic_signed_at: datetime?, dispatcher_signed_at: datetime?
  reviewed_by: string?
  destination_risk: enum(low, moderate, high, extreme)?
  ground_security: enum(normal, elevated, high_threat, critical)?
  overwater_legs: boolean
  etp_waypoint: string?
  customs_status: enum(not_required, pending, cleared, denied)?
  created_at: datetime
  updated_at: datetime
  amended_at: datetime?
  closed_at: datetime?
}
```

### 3.12 Audit Log

```
AuditLog {
  id: UUID (PK)
  organization_id: UUID (FK)
  user_id: UUID? (null for system actions)
  action: string (e.g. "flight.created", "maintenance.completed")
  entity_type: string, entity_id: UUID
  old_values: JSONB?, new_values: JSONB?
  ip_address: string?, user_agent: string?
  created_at: datetime
}
```

### 3.13 Mission / Flight Leg (Multi-Leg Planning)

```
Mission {
  id: UUID (PK)
  organization_id: UUID (FK)
  name: string
  status: enum(draft, active, completed, cancelled)
  aircraft_id: UUID? (FK)
  created_by: string? (user ID)
  created_at: datetime
  updated_at: datetime
}

FlightLeg {
  id: UUID (PK)
  mission_id: UUID (FK)
  leg_index: integer
  origin: string (ICAO), destination: string (ICAO)
  scheduled_departure: datetime?
  scheduled_arrival: datetime?
  actual_departure: datetime?
  actual_arrival: datetime?
  flight_time_minutes: float?
  status: enum(scheduled, active, completed, cancelled)
  notes: text?
}
```

---

## 4. Module Specifications — Current Build Status

All 11 Phase 1 modules are **built and operational**. Below is what was actually delivered for each.

### Module 1: Auth & Organization Setup — COMPLETED

- **JWT access tokens** (480min TTL, configurable) + **refresh tokens** (7 day TTL)
- **MFA via TOTP** (pyotp) — optional per user, encrypted at rest
- **11-role RBAC** — `app/core/roles.py` with `FEATURE_PERMISSION_MATRIX` in `app/core/features.py` (26 features, 12 categories)
- **Organization isolation** — all entities scoped to `organization_id`
- **Invite codes** with multi-role selection + per-user feature overrides
- **Bootstrap code** (`PARARIG-ADMIN-2026`) for creating the first admin
- **Bulk user import** via CSV
- **Password hashing** (bcrypt), **email/password login**
- **Audit log** for auth events

### Module 2: Fleet Configuration — COMPLETED

- Aircraft CRUD with full config (weights, performance, capabilities)
- Component tracking (engines, props, landing gear, batteries, avionics, APU, hydraulic)
  - TBO tracking (hours + cycles + calendar)
  - Life-limited part (LLP) tracking
  - Hours/cycles since overhaul
- CSV bulk import for aircraft
- Status badges (active/in_maintenance/grounded/retired/stored)
- Insurance tracking (provider, policy, expiry, coverage amount)
- Registration/airworthiness/CofA expiry tracking

### Module 3: Maintenance Tracking — COMPLETED

- Maintenance task library (scheduled/in_progress/completed/overdue/deferred)
- Interval tracking (hours + calendar days)
- AD/SB compliance tracker (`ad_compliance.py` — real ADs for King Air 350/200, DHC-6 Twin Otter, Basler BT-67)
- Expiry Center (`GET /api/v1/compliance/expiry-center?window_days=30`) — read-only aggregation of aircraft expiries (registration/airworthiness/COA/insurance), component TBO (calendar + hours), crew license/medical/passport, qualifications, documents, and per-aircraft AD/SB summary. Powers the Discord Compliance Watch cron (daily 08:20). Phase 1 of `EXPIRY_CENTER_SCOPE.md`; Phase 3 (frontend page) and Phase 4 (computed pilot currency) pending.
  - Severity-grounded: critical (grounded), major (time-limited), minor (informational), optional (SB)
  - Compliance methods: one-time, recurring by hours, cycles, calendar, or both
- Maintenance dashboard endpoint (due/overdue with color-coded alerts)
- Task types: inspection, oil_change, ad, sb, overhaul, repair, annual, 100hr, phase
- Maintenance release signoff (Safe for Flight) integrated into flight release workflow
- Gripe system (open/deferred gripes as JSON on flight release)
- Deferred maintenance (MEL) workflow

### Module 4: Flight Operations & Scheduling — COMPLETED

- Multi-leg mission planning (Mission + FlightLeg model, status lifecycle)
- Route planner (`POST /api/v1/routes/plan`):
  - Per-leg: distance (haversine), block time, fuel burn, capabilities check
  - Weight & balance per leg
  - Crew duty time compliance (FAR 135.267/271)
  - Per-destination: METAR/TAF weather brief via AviationWeather.gov
  - NOTAM retrieval via FAA NMS API
  - Cash estimates (fuel, handling, landing, customs, misc costs)
  - Mission totals: time, fuel, distance, critical flags
- Flight releases with 3-gate signoff (Maintenance → PIC → Dispatcher):
  - Release number (auto-generated FR-YYYY-NNN)
  - Crew duty start/end tracking
  - Fuel planning (ramp, trip, contingency, alternate, reserve, arrival fuel — all in lbs)
  - Fuel legality check
  - Gripes (open + deferred)
  - Weather brief + NOTAM refs as JSON
  - Destination risk assessment (hot-zone: low/moderate/high/extreme)
  - Ground security levels (normal/elevated/high_threat/critical)
  - Overwater leg detection + ETP waypoint
  - Customs status tracking
  - Amended/closed lifecycle
- Airport database with auto-lookup from OurAirports (`airport_lookup.py`)
- Route library (frequent routes)
- Flight status tracking (scheduled/active/completed/cancelled/diverted)
- Ops checks endpoint

### Module 5: Crew Management — COMPLETED

- Crew member profiles (license, medical, passport, visa data)
- 13-member seed data with full profiles
- Qualification tracking with expiry alerts (type ratings, proficiency checks, recurrent training, etc.)
- Aircraft-type matching via CrewQualification.aircraft_id
- Duty time calculator (FAR 135.267 enforcement):
  - 8hr flight time in 24hr (single-pilot) / 10hr (2-pilot)
  - 14hr maximum duty period
  - Minimum 10hr consecutive rest
  - Quarterly/annual flight hour limits (500/800/1400)
- Crew currency metrics (90-day, 12-month hours/landings)
- Logbook entries

### Module 6: Compliance & Document Management — COMPLETED

- Document upload with metadata (type, authority, expiry)
- Expiration tracking (color-coded: current/expiring_soon/expired)
- Document status management
- Compliance checklist per route (auto-calculated via route planner)
- Document types cover: airworthiness cert, registration, insurance, operating specs, Caribbean waivers, customs clearance, noise cert, export cert, dry lease, crew license, medical, training records, ops manual, MEL
- Reminder days (configurable per document)

### Module 7: Financial Dashboard — COMPLETED

- FinancialRecord model (revenue/cost/invoice/expense) with auto-creation from flights
- P&L per tail number
- Cost categories: fuel, maintenance, crew, insurance, landing fees, handling, hangar, training, customs, misc
- Mission P&L endpoint (estimated vs actual reconciliation)
- Leg-level cost tracking (LegCost model — fuel, handling, landing, customs, parking, misc per leg)
  - Payment method tracking (cash/credit/credit_card/wire)
  - Receipt URL support
  - Logged-by attribution
- Cost reporting endpoints

### Module 8: Operation Center — COMPLETED

- MapLibre GL map with dark-matter style tiles
- 10 toggleable layers:
  1. Fleet (aircraft positions)
  2. Routes (planned/active route lines)
  3. Fuel rings (range rings)
  4. Weather (METAR overlay)
  5. NOTAMs
  6. Progress tracker (mission progress)
  7. Trails (aircraft trail history)
  8. Airports
  9. ETP markers (Equal Time Points for overwater)
  10. Radar overlay
- Live ADS-B tracking via ADSB.lol / OpenSky API
- Emergency alert dialog
- In-app crew messaging (WebSocket notification bus)
- METAR/NOTAM briefing display

### Module 9: Comms & Emergency Alerting — COMPLETED

- WebSocket notification bus — real-time push to connected clients
- Notification model (persistent, with read status)
- Emergency alert with escalation support
- Configurable: Twilio SMS support (optional), SMTP email (optional)

### Module 10: Onboarding Wizard — COMPLETED

- Invite code system with multi-role selection
- Per-user feature overrides on invite
- Onboarding wizard React component (feature/onboarding/)
- Bootstrap code for first admin creation
- Bulk CSV user import

### Module 11: AI Help Desk — COMPLETED

- In-app chat interface (HelpdeskPanel — collapsible modal)
- Context-aware queries via integrated AI agent
- Pre-built Q&A templates for common operations questions

### Module 12: White-Label / Multi-Tenant (Phase 2 — Not Yet Built)

- Organization branding: partial (logo_url field exists, no full theming UI)
- Custom subdomain: planned
- Custom email templates: planned
- Feature flags per tenant: partial (settings JSONB on Organization)
- Usage/billing tier management: planned
- Self-hosted license key generation: planned

---

## 5. API Endpoints (Registered Routes)

All routes are mounted under `/api/v1` prefix. OpenAPI docs auto-generated at `/docs`.

```
# Auth
POST   /api/v1/auth/login
POST   /api/v1/auth/register
GET    /api/v1/auth/me
POST   /api/v1/auth/refresh
POST   /api/v1/auth/mfa/setup
POST   /api/v1/auth/mfa/verify
POST   /api/v1/auth/mfa/disable

# Onboarding
POST   /api/v1/onboarding/bootstrap     # First admin via bootstrap code
POST   /api/v1/onboarding/invite         # Create invite code
POST   /api/v1/onboarding/accept-invite  # Accept invite

# Help Desk
POST   /api/v1/helpdesk/query            # AI query endpoint

# Aircraft
GET    /api/v1/aircraft
POST   /api/v1/aircraft
GET    /api/v1/aircraft/{id}
PATCH  /api/v1/aircraft/{id}
DELETE /api/v1/aircraft/{id}
GET    /api/v1/aircraft/{id}/components
POST   /api/v1/aircraft/{id}/components
PATCH  /api/v1/aircraft/{id}/components/{component_id}

# Airports
GET    /api/v1/airports                   # Search/lookup airports
GET    /api/v1/airports/{icao}            # Airport detail

# Routes
GET    /api/v1/routes                     # Route library
POST   /api/v1/routes                     # Create route
POST   /api/v1/routes/plan                # Full route planner (W&B, crew, weather, NOTAMs, costs)

# Maintenance
GET    /api/v1/maintenance
POST   /api/v1/maintenance
GET    /api/v1/maintenance/{id}
PATCH  /api/v1/maintenance/{id}
DELETE /api/v1/maintenance/{id}
GET    /api/v1/maintenance/due            # Due tasks
GET    /api/v1/maintenance/overdue        # Overdue tasks

# Maintenance Dashboard
GET    /api/v1/maintenance/dashboard      # Aggregated maintenance dashboard

# Flights
GET    /api/v1/flights
POST   /api/v1/flights
GET    /api/v1/flights/{id}
PATCH  /api/v1/flights/{id}
DELETE /api/v1/flights/{id}
GET    /api/v1/flights/active             # Currently active flights

# Flight Releases
GET    /api/v1/flight-releases
POST   /api/v1/flight-releases
GET    /api/v1/flight-releases/{id}
PATCH  /api/v1/flight-releases/{id}
POST   /api/v1/flight-releases/{id}/sign/maintenance   # Gate 1 signoff
POST   /api/v1/flight-releases/{id}/sign/pic            # Gate 2 signoff
POST   /api/v1/flight-releases/{id}/sign/dispatcher     # Gate 3 signoff
POST   /api/v1/flight-releases/{id}/amend               # Amend release

# Crew
GET    /api/v1/crew
POST   /api/v1/crew
GET    /api/v1/crew/{id}
PATCH  /api/v1/crew/{id}
DELETE /api/v1/crew/{id}
GET    /api/v1/crew/{id}/qualifications
POST   /api/v1/crew/{id}/qualifications
GET    /api/v1/crew/available             # Available crew lookup

# Compliance / Documents
GET    /api/v1/compliance/documents
POST   /api/v1/compliance/documents
GET    /api/v1/compliance/documents/{id}
PATCH  /api/v1/compliance/documents/{id}
DELETE /api/v1/compliance/documents/{id}
GET    /api/v1/compliance/expiring        # Expiring documents

# Communications
GET    /api/v1/comms/notifications        # User notifications
POST   /api/v1/comms/notifications/{id}/read
POST   /api/v1/comms/emergency            # Trigger emergency alert
WS     /api/v1/comms/ws                   # WebSocket connection

# Finance
GET    /api/v1/finance/records
POST   /api/v1/finance/records
GET    /api/v1/finance/pnl               # P&L by tail
GET    /api/v1/finance/pnl/mission/{id}   # Mission P&L
GET    /api/v1/finance/summary            # Financial summary

# Tracking (ADS-B)
GET    /api/v1/tracking/positions         # Live aircraft positions
GET    /api/v1/tracking/history/{tail}    # Position history

# Ops Checks
GET    /api/v1/ops-checks
POST   /api/v1/ops-checks

# Missions
GET    /api/v1/missions
POST   /api/v1/missions
GET    /api/v1/missions/{id}
PATCH  /api/v1/missions/{id}
DELETE /api/v1/missions/{id}
POST   /api/v1/missions/{id}/legs
PATCH  /api/v1/missions/{id}/legs/{leg_id}
DELETE /api/v1/missions/{id}/legs/{leg_id}

# Passengers
GET    /api/v1/passengers
POST   /api/v1/passengers
GET    /api/v1/passengers/{id}
PATCH  /api/v1/passengers/{id}
DELETE /api/v1/passengers/{id}

# Users
GET    /api/v1/users
GET    /api/v1/users/{id}
PATCH  /api/v1/users/{id}
DELETE /api/v1/users/{id}

# Organization Settings
GET    /api/v1/org/settings
PATCH  /api/v1/org/settings

# Admin
GET    /api/v1/admin/users
POST   /api/v1/admin/invite
PATCH  /api/v1/admin/users/{id}/role
PATCH  /api/v1/admin/users/{id}/features  # Update feature overrides

# Bulk Import
POST   /api/v1/bulk-import/aircraft
POST   /api/v1/bulk-import/crew
POST   /api/v1/bulk-import/users

# Export
GET    /api/v1/export/flights
GET    /api/v1/export/finance
GET    /api/v1/export/crew

# Logbook
GET    /api/v1/logbook
POST   /api/v1/logbook
GET    /api/v1/logbook/{id}
PATCH  /api/v1/logbook/{id}

# Reports
GET    /api/v1/reports/flight-summary
GET    /api/v1/reports/maintenance-summary

# Weather / Briefing
GET    /api/v1/weather/metar/{icao}
GET    /api/v1/weather/taf/{icao}
GET    /api/v1/weather/notams/{icao}

# Costs
GET    /api/v1/costs
POST   /api/v1/costs

# Leg Costs
GET    /api/v1/leg-costs
POST   /api/v1/leg-costs
GET    /api/v1/leg-costs/by-leg/{leg_id}

# Briefing
GET    /api/v1/briefing/{mission_id}      # Full mission briefing

# Permissions
GET    /api/v1/permissions/my             # Current user's effective permissions
GET    /api/v1/permissions/features       # All known features

# Health
GET    /health                            # Health check
```

---

## 6. UI/UX Design Language

### Design System
- **Panel** — shadcn/ui components (consistent, accessible)
- **Dark mode first** — aviation ops centers run dark, respect that
- **Sidebar navigation** — collapsible sidebar with icon + label, 14 nav items
- **Responsive** — works on desktop and tablet

### Key Screens (Built)

**Dashboard** — Morning Brief page (default route `/`)
- Today's flights, weather, maintenance alerts, financial snapshot
- Quick-action buttons

**Fleet Dashboard** (`/fleet`)
- Grid of aircraft cards with color-coded status
- Each card: tail number, type, status badge, hours
- Click through to Aircraft Detail (`/fleet/:id`)
- Tabs: Overview | Components | Maintenance | Flights | Financial

**Airport Lookup** (`/airports`)
- Searchable airport database with ICAO codes, coordinates, FBOs

**Missions** (`/missions`)
- List of multi-leg missions with status
- Mission Builder (`/missions/new`) — route planning with leg builder
- Mission Detail (`/missions/:id`) — per-leg tracking, status, crew

**Dispatch** (`/dispatch`)
- Flight release management
- Release detail with 3-gate signoff workflow

**Operation Center** (`/operations`)
- MapLibre GL dark-matter map with 10 toggleable layers
- Live ADS-B aircraft positions
- Emergency alert button
- In-app messaging

**Maintenance** (`/maintenance`)
- Maintenance task list with due/overdue counters
- Task creation and completion

**Maint Control** (`/maint-control`)
- Maintenance dashboard view
- AD/SB compliance overview

**Personnel** (`/crew`)
- Crew member list with qualification status
- Crew Detail (`/crew/:id`) — full profile, qualifications, currency

**Compliance** (`/compliance`)
- Document upload and expiration tracking
- Color-coded status badges

**Finance** (`/finance`)
- P&L summary, cost records, per-mission financials

**User Permissions** (`/admin/users`)
- User management with role assignment
- Feature override management

**Admin Panel** (`/admin`)
- System settings, invite code generation

**Help Desk** — in-app collapsible chat panel

---

## 7. Security

### Auth & Access
- bcrypt password hashing (work factor 12)
- JWT access tokens (480min TTL) + refresh tokens (7 day TTL, rotate on use)
- MFA via time-based OTP (TOTP) — authenticator app
- RBAC enforced at router level + service layer via `require_role()` / `require_feature()` dependencies
- Feature-level permission overrides per user (`feature_overrides` JSON on User model)
- PII clearance flag for sensitive passenger data access
- Session invalidation on password change

### API Security
- CORS restricted to frontend origin (configurable)
- All requests logged to audit log (who, what, when, IP, user-agent)
- SQLAlchemy parameterization — no raw SQL by convention
- Rate limiting on auth endpoints

### Data Security
- All passwords hashed, never stored plaintext
- MFA secrets encrypted at rest (AES-256)
- Local file storage for document uploads (S3/Minio swap possible)
- Audit trail immutable (append-only pattern)

### Infrastructure
- Caddy auto-TLS for HTTPS
- Docker secrets for sensitive env vars
- UFW on host: only SSH + Docker bridge open
- Tailscale recommended for admin access
- `TrustedHostMiddleware` in production

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
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]

  frontend:
    build: ./frontend
    depends_on: [backend]

  caddy:
    image: caddy:2-alpine
    ports: [80:80, 443:443]
    volumes: [./Caddyfile:/etc/caddy/Caddyfile, caddy_data:/data]
```

### Development (No Docker)

```bash
# Backend
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Environment Variables

```
# Database
DATABASE_URL=sqlite+aiosqlite:///./pararig_ops.db    # Dev
DATABASE_URL=postgresql+asyncpg://pararig:${DB_PASSWORD}@postgres:5432/pararig_ops  # Prod

# Auth
SECRET_KEY=<random-64-char-hex>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
REFRESH_TOKEN_EXPIRE_DAYS=7
MFA_ENCRYPTION_KEY=<random-32-char>

# Onboarding
INVITE_BOOTSTRAP_CODE=PARARIG-ADMIN-2026

# External APIs
FAA_NMS_CLIENT_ID=         # FAA NOTAM API client ID
FAA_NMS_CLIENT_SECRET=     # FAA NOTAM API secret
TWILIO_ACCOUNT_SID=        # Optional SMS
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=

# Email (optional)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=

# Instance
ENVIRONMENT=dev|prod
INSTANCE_MODE=self_hosted|saas
```

---

## 9. Development Roadmap — Current Status

### Phase 1 — Core Build (COMPLETED ✅)

All 11 Phase 1 modules have been built and are operational. The system is running on the development stack and has been populated with seed data for a Caribbean Part 135 operation (2 aircraft, 13 crew members, multiple mission types).

**Delivered:** A full-stack system usable day one for a 2-aircraft Nassau ↔ Haiti operation. Manage aircraft, schedule missions, dispatch flights through a 3-gate release workflow, log maintenance, track crew currency, handle BCAA/Haiti compliance, see real-time P&L, and monitor operations on a live ADS-B map with emergency alerting.

### Phase 2 — Hardening & Polish (CURRENT)

- [ ] PostgreSQL production migration (currently using SQLite for dev)
- [ ] PWA offline mode (service worker, cached routes) — frontend scaffold exists
- [ ] Email notifications (SendGrid/Resend) — SMTP config exists, need actual integration
- [ ] SMS notifications (Twilio) — config exists, need actual integration
- [ ] QuickBooks sync (API integration)
- [ ] PDF manifest/invoice/flight release generation
- [ ] Multi-base support
- [ ] In-app audit log viewer
- [ ] Performance optimization (query tuning, indexing audit)
- [ ] Test coverage expansion (auth tests exist, need more)
- [ ] Delete lockdown — enforce draft-only delete on active/completed missions
- [ ] Digital checklists — per-aircraft-type preflight/post-flight templates
- [ ] Designated Part 135 positions management
- [ ] Inventory/parts system

### Phase 3 — Advanced (Future)

- AI Help Desk full deployment (deep Hermes integration)
- White-label + multi-tenant billing (Module 12)
- SaaS billing (Stripe integration — config exists)
- Advanced analytics & forecasting
- SATCOM / Iridium comms integration
- Custom reporting engine
- Calendar integration (Google Calendar / iCal export)

---

## 10. Development Standards

### Python / Backend
- Type hints everywhere
- Async endpoints (FastAPI async handlers)
- Pydantic v2 for all schemas
- Repository/service pattern for data access
- Unit tests with `pytest` + `httpx.AsyncClient`
- Coverage target: 80%+
- Black + Ruff for formatting/linting (in pyproject.toml)

### TypeScript / Frontend
- Strict mode TypeScript
- React Query for all server state
- React Router v7 for routing
- shadcn/ui + Radix Primitives components
- Maplibre GL for maps
- Tailwind CSS 4 for styling

### Database
- Alembic for migrations (always reversible)
- All timestamps UTC
- Indexes on all foreign keys + commonly queried columns
- JSONB for flexible metadata
- Use ENUM types for bounded values

### Git
- Branch: `main` (stable), `develop` (active), feature branches
- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`
- Sqash-merge feature branches into develop

---

## 11. Dependencies & Integrations (Actual)

### Current
- **PostgreSQL 16 / SQLite** — primary database
- **AviationWeather.gov (NOAA/FAA ADDS)** — free METAR/TAF weather (no API key)
- **FAA NMS API** — NOTAM retrieval (OAuth2, free with registration)
- **OurAirports** — airport database (data imported locally)
- **MapLibre GL** — maps (dark-matter style, free tile source)
- **ADSB.lol / OpenSky Network** — live ADS-B aircraft tracking
- **Local filesystem** — document storage (S3/Minio swap possible)

### Configured but Not Yet Active
- **Twilio** — SMS notifications (config exists, not wired)
- **SMTP** — email notifications (config exists, not wired)
- **Stripe** — SaaS payments (config exists, Phase 3)

---

## 12. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| SQLite won't support concurrent writes | Medium | Low | Use PostgreSQL in production, SQLite only for single-user dev |
| Multi-tenant data isolation bug | Low | High | Each query scoped to `organization_id` — enforce at middleware level |
| Offline sync is hard | High | Medium | Postpone full offline to Phase 2; use simple cached reads in MVP |
| Regulatory compliance varies by country | Medium | Medium | Flexible document tagging system — don't hardcode any country logic |
| ADS-B feed reliability | Low | Medium | Multiple data sources (ADSB.lol + OpenSky), graceful fallback |
| FAA NMS API changes | Low | Medium | NOTAM service isolated behind `services/weather.py` — swap provider |
| Flight release signoff race conditions | Low | Medium | Status-based state machine prevents double-signoff from conflicting gates |

---

## 13. Current State & Next Steps

**The specification has been signed off.** All Phase 1 modules are built and operational. The system currently runs on SQLite in development mode, has been tested with seed data for a Caribbean Part 135 operation (Nassau ↔ Haiti), and includes real-world AD data for the King Air 350/200, DHC-6 Twin Otter, and Basler BT-67 fleets.

**Immediate priorities (Phase 2):**
1. Migrate to PostgreSQL for production
2. Wire up SMTP email notifications (config exists, backend ready)
3. Wire up Twilio SMS for emergency alerts (config exists, backend ready)
4. Add PDF generation for flight releases, manifests, and invoices
5. Expand test coverage beyond auth tests
6. Implement in-app audit log viewer
7. Performance pass: query optimization, index review

**Known gaps tracked in FEATURE_BACKLOG.md:**
- Digital preflight/post-flight checklists
- Designated Part 135 positions management (DO, Chief Pilot, DOM)
- Inventory/parts system
- Calendar integration (maintenance, crew duty, flight schedules)
- Cost-per-flight-hour analytics
- Utilization reports
