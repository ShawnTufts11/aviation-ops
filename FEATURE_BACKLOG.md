# ParaRig Ops — Feature Backlog

_Collected from conversations. Evaluate, prioritize, or defer per session._

## Core Ops (ready when you are)

- [ ] **Flight logging** — log actual departure/arrival, fuel used, crew assignment against a mission. Feeds into currency tracking and cost per hour.
- [ ] **Tracking → mission wiring** — ADSB.lol live positions already work on dashboard, wire them into active mission view so dispatchers see the actual aircraft en route.

## Compliance & Safety

- [x] **Expiry Center (Phases 1-2, DONE 2026-08-25)** — unified expiry aggregation API (`GET /api/v1/compliance/expiry-center`) + Discord Compliance Watch cron (daily 08:20, #command-center). Scope: `EXPIRY_CENTER_SCOPE.md`.
- [ ] **Expiry Center Phase 3** — frontend: extend CompliancePage with aircraft/crew/qual sections + color-coded days-left (see EXPIRY_CENTER_SCOPE.md)
- [ ] **Expiry Center Phase 4** — computed pilot currency (90-day landings, 24-month flight review) from logbook
- [ ] **Expiry Center Phase 5** — PDF compliance report export for 135 operators

- [ ] **Digital checklists** — per-aircraft-type preflight/post-flight templates. PIC signature required before release or duty completion. Configurable by OPS_MANAGER.
- [ ] **Designated Part 135 positions** — DO, Chief Pilot, DOM, Chief Inspector, Training Manager. Named individuals with appointment dates and qualification docs. Slots can be vacant without blocking anything.
- [ ] **Qualification path display** — show the current FAA requirements for each designated position (what licenses, ratings, experience needed). Pull from a trusted source if possible, or maintain manually.
- [ ] **Delete lockdown** — after testing, re-enable the draft-only delete restriction so completed/active missions can't be removed. Audit log retains the trail regardless.

## Logistics & Inventory

- [ ] **Inventory/parts system** — track parts by location, cost, quantity. Move between bases. Forecast needs based on inspection cycles and maintenance intervals. Research whether an existing open-source system integrates (e.g. PartsBase, Odoo inventory, or a lightweight custom build).

## Calendar & Scheduling (final stamp)

- [ ] **Separate calendars** — maintenance, flights, crew duty, training/qual expiries
- [ ] **Master calendar** — overlay view showing everything
- [ ] **Crew scheduling** — schedule on-duty, off-duty, time off, track flight hours against 90-day/12-month currency
- [ ] **Maintenance scheduling** — inspection intervals, due dates, parts lead times

## Reports & Analytics

- [ ] **Cost per flight hour** — needs utilization data (flights × block time) + finance (fuel, maintenance, crew) wired together
- [ ] **Utilization reports** — which aircraft fly the most, which pilots fly what, route frequency analysis

## Audit & Compliance Trail

- [x] **Audit log** — already exists (`log_action` table). Tracks who did what and when. Covers crew creation, mission changes, and now mission deletion.
