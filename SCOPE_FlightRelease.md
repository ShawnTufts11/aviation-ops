# Flight Release / Dispatch Page — Scope Document

## Mission Context

ParaRig Aviation Operations Suite is a civilian airlift platform designed for transporting
supplies and personnel into hot-zone environments — starting with Haiti operations based out of
MYNN (Nassau). This is the compliance and planning layer for a lean, multi-aircraft 135-style
operation operating alongside or in lieu of traditional dispatch software.

The initial deliverable is a **Flight Release / Dispatch Page** — the core document produced
before every flight leg. But it lives within a larger operational model:

**Three-tier gate system:**
1. **Maintenance Control** signs "Safe for Flight" — aircraft is airworthy for the intended mission
2. **PIC** accepts the aircraft — may find gripes during preflight, triggering a maintenance loop
3. **Dispatch / Flight Planner** releases the flight — route, weather, fuel, crew, and cargo all legal

**The Maintenance Control loop:**
```
Pre-flight:
  Maintenance Control signs "Safe for Flight"
  → PIC preflight (may find gripes)
  → If gripes: Maintenance Control dispatches mechs → fix → re-sign
  → Once clean: PIC accepts aircraft
  → Dispatch releases the flight

Post-flight:
  Pilot reports in-flight gripes (post-landing)
  → Maintenance Control decides: fix now or defer?
     (based on flight schedule, parts availability, personnel)
  → Feeds into the aircraft scheduling queue
```

**Mission Capability (per aircraft):**
- **Full Mission Capable** — no restrictions, any mission type
- **Partial Mission Capable** — airworthy but restricted;
  e.g. autopilot inop = no single-pilot IFR,
  or cargo door actuator slow = cargo missions only, no passenger
- **Not Mission Capable** — downing discrepancy, awaiting maintenance

This mirrors the military concept where an aircraft could fly a cargo mission
but not an anti-submarine mission depending on which systems were functional.
For ParaRig: a BT-67 with a minor cargo door issue might still fly passengers
but not carry bulk supplies — the system needs to understand that distinction.

## User Roles

| Role | Authority | Signed items |
|------|-----------|-------------|
| **Base Ops Manager/VP** | Oversees all ops, maintenance, dispatch, crew. Coordinator role — not a pilot or mechanic cert holder. | Management review of release |
| **Maintenance Controller** | Signs aircraft safe-for-flight, dispatches mechs to fix gripes, defers items per MEL/CDL | Safe-for-Flight cert, gripes log |
| **Dispatch / Flight Planner** | Routes, weather, fuel, NOTAMs, duty compliance, releases flight | Dispatch release signature |
| **PIC** | Accepts aircraft, responsible for safe operation, may reject aircraft | Aircraft acceptance, PIC signature |
| **SIC** | Assists PIC, fills second seat when required | (optional, per flight)

## Aircraft Fleet

| Tail | Type | Typical Role |
|------|------|-------------|
| BT-67 | Basler (DC-3 conversion) | Cargo / heavy lift, austere strips |
| KA350 | King Air 350 | Passenger / medevac / light cargo |
| K200 | King Air 200 | Passenger / light cargo |
| T300 | Cessna 208 Caravan | Single-pilot cargo, short fields |

Each aircraft type has its own performance profile (cruise speed, fuel burn, max payload, takeoff/
landing distance, required runway length, usable fuel capacity).

## Data Sources (Live)

| Source | Data | Status |
|--------|------|--------|
| AviationWeather.gov | METAR, TAF, winds aloft, SIGMETs, AIRMETs | ✅ Free, no key |
| FAA NMS NOTAM API | NOTAMs, TFRs, airspace restrictions | ✅ OAuth creds in .env |
| Local aircraft DB | Tail numbers, config, airworthiness, cycle counts | ✅ Needs maintenance tracking |
| Crew DB | Pilot quals, medical, currency, duty logs | ✅ Basic structure exists |
| Route planner | Multi-leg route with waypoints & distances | ✅ Proto endpoint at /api/v1/routes/plan |

## Page Layout (Proposed)

```
┌─────────────────────────────────────────────────────────┐
│  PARARIG AVIATION OPERATIONS     FLIGHT RELEASE #FR-xxx  │
│  Flight Release / Dispatch Authorization                 │
├─────────────────────────────────────────────────────────┤
│  FLIGHT IDENTITY                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Date: ____  Leg: 1 of N   Mission: ____________  │    │
│  │ Aircraft: [AC dropdown]  Tail: [auto-filled]    │    │
│  │ Route: [origin] → [dest]  Alt: [altn]           │    │
│  │ Departure: ___Z  Est Enroute: ___h___m          │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  CREW ASSIGNMENT & DUTY                                 │
│  ┌─────────────────────────────────────────────────┐    │
│  │ PIC: [select]  SIC: [select]  (optional)        │    │
│  │ PIC Duty Day: ___h / 14h   SIC Duty: ___h / 14h │    │
│  │ Last 7 days: PIC ___h   SIC ___h                │    │
│  │ ⚠ DUTY CHECK: [PASS] / [EXCEEDED]              │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ROUTE & NAV LOG                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Waypoint   | Course | Dist nm | ETA | Fuel Rem │    │
│  │ MYNN       |    —   |   —     | —   |  FOB  2200│    │
│  │ MARLIN     | 152°   |   45    | 12:15Z |  2050  │    │
│  │ ETROG      | 180°   |   55    | 12:28Z |  1900  │    │
│  │ MTPP       | 175°   |   35    | 12:38Z |  1780  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  WEATHER BRIEF                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ DEPARTURE: MYNN  METAR: ...  TAF: ...          │    │
│  │ DEST: MTPP      METAR: ...  TAF: ...           │    │
│  │ ALTN: MTCH      METAR: ...  TAF: ...           │    │
│  │                                                    │
│  │ ROUTE WEATHER:                                     │
│  │ SIGMET X... (if any)  WINDS: 260/35kt @FL180      │
│  │ ⚠ GO/NO-GO: [RECOMMENDED] / [HOLD — see notes]   │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  NOTAMS & AIRSPACE                                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ACTIVE NOTAMS: N items                           │    │
│  │ · ...                                            │    │
│  │ · ...                                            │    │
│  │ AIRSPACE:                                        │    │
│  │ · TFR: ...  ACTIVE ___ to ___Z                   │    │
│  │ · Restricted area: ...                           │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  FUEL PLAN                                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Ramp:  2200 lbs   (above ___lbs)                │    │
│  │ Trip:  -500                                       │    │
│  │ Contingency (5%): -25                             │    │
│  │ Alternate: -180                                   │    │
│  │ Final reserve: -300                               │    │
│  │ ─────────────────────                             │    │
│  │ Fuel on arrival: 1195 lbs                         │    │
│  │ ⚠ LEGAL FUEL: [PASS] / [REQUIRES FUEL STOP]      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  HAZARD / HOT-ZONE ASSESSMENT                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Destination risk: [Low / Medium / High]         │    │
│  │ Ground security: [Coordinated / Unescorted]     │    │
│  │ Overwater legs: N   ETP at waypoint ___        │    │
│  │ Customs: [Cleared / Pending / N/A]              │    │
│  │ Passenger/cargo manifest attached: [Link]       │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  AUTHORIZATIONS                                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │ PIC SIGNATURE: ___________  DATE: ______        │    │
│  │ DISPATCHER: ______________  TITLE: ______       │    │
│  │ REVIEWED BY: ____________  (Mgt/Ops)            │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  STATUS: [DRAFT] [RELEASED] [AMENDED] [CLOSED]         │
├─────────────────────────────────────────────────────────┤
│  Generated by ParaRig Ops Engine — ${DATE}              │
│  Flight Release #FR-xxx — Revision 0                    │
└─────────────────────────────────────────────────────────┘
```

## Data Model (Backend)

### Flight Release
```
FlightRelease {
  id: UUID
  release_number: string      // FR-2026-001
  status: draft | released | amended | closed
  mission_name: string
  date: date
  leg_number: int
  total_legs: int
  
  // Aircraft
  tail_number: string
  aircraft_type: BT-67 | KA350 | K200 | T300
  
  // Route
  origin_icao: string
  dest_icao: string
  alternate_icao: string
  route_waypoints: Waypoint[]
  
  // Times
  departure_time: datetime (Z)
  est_enroute_minutes: int
  etas: WaypointETA[]
  
  // Crew
  pic_id: UUID
  sic_id: UUID | null
  pic_duty_current: int       // hours into current duty day
  sic_duty_current: int
  pic_duty_7day: int
  sic_duty_7day: int
  duty_compliant: boolean
  
  // Weather (snapshot at release time)
  weather_brief: WeatherBrief
  
  // Fuel
  fuel_ramp_lbs: float
  fuel_trip_lbs: float
  fuel_contingency_lbs: float
  fuel_alternate_lbs: float
  fuel_final_reserve_lbs: float
  fuel_on_arrival_lbs: float
  fuel_legal: boolean
  
  // Hot-zone
  destination_risk: low | medium | high
  ground_security: coordinated | unescorted
  overwater_legs: int
  etp_waypoint: string | null
  customs_status: cleared | pending | na
  
  // Maintenance Control
  safe_for_flight: boolean
  safe_for_flight_signed_by: string | null
  safe_for_flight_signed_at: datetime | null
  mission_capability: full | partial | not_capable
  mission_capability_restrictions: string[]
  gripes_open: Gripe[]
  gripes_deferred: Gripe[]
  gripe_count_open: int
  gripe_count_deferred: int

  // Authorization
  pic_accepted: boolean
  pic_accepted_at: datetime | null
  pic_signed_at: datetime | null
  dispatcher_signed_at: datetime | null
  reviewed_by: string | null
  
  created_at: datetime
  amended_at: datetime | null
  closed_at: datetime | null
}
```

### Waypoint
```
Waypoint {
  ident: string               // MYNN, MARLIN, MTPP, etc.
  lat: float
  lon: float
  is_etp: boolean             // equal-time point for overwater
  is_avoidance: boolean       // threat/customs boundary
}
```

### WeatherBrief (snapshot)
Structured data pulled from AviationWeather.gov at release time. Contains METAR, TAF, winds
aloft, SIGMETs, AIRMETs for origin, destination, and alternates.

### NOTAMSet
All active NOTAMs and TFRs along the route at release time, from the FAA NMS API.

## Open Questions

### Operations / Workflow
1. **Who releases the flight?** Does the pilot self-dispatch (common in smaller 135 ops), or is there a dedicated dispatcher role on paper?
2. **Do we need a manifest/cargo page** as a separate view, or embedded in the release? You mentioned supplies into Haiti — manifests for customs are critical.
3. **Should the release be editable after issuance** (amendments), or is each flight one-and-done with amendments tracked as separate versions?
4. **What's the minimum you'd want to see** in a demo to an operator? All fields filled with real data on one route (MYNN→MTPP), or a specific route you have in mind?

### Aircraft Data
5. **Performance profiles per aircraft type** — we need cruise speed, fuel burn per phase, max takeoff weight, max payload, and usable fuel capacity. Do you have these numbers handy or do we use published spec data?

### Hot-Zone Specific
6. **The "hot zone assessment" section** — what signals matter to you? Security clearance at destination? Whether ground support is pre-arranged? I designed the section based on what would matter for Haiti ops, but want your eyes on it.

### Integration
7. **Do you want this as an MC page first** (web dashboard within Mission Control), or as a standalone printable page that lives at `/dispatch/release`? My recommendation is MC page for iteration speed, then we can expose a print/PDF endpoint.

## Build Priority

**V1: Core Release Form** — aircraft info, route, crew, duty check, fuel plan, signatures, print/PDF. No live weather or NOTAMs yet — hardcode the example data. Get the form layout right.

**V2: Live Data** — wire in METAR/TAF from AviationWeather.gov, NOTAMs from FAA API, auto-populate weather section. Add go/no-go logic.

**V3: Hot-Zone Overlays** — threat assessment, ground security coordination, customs tracker, overwater ETP calculator. This is where the civilian airlift capability differentiates from ForeFlight.

**V4: Manifest & Cargo** — separate page or embed for passenger/cargo manifests per leg, with customs declaration fields.

## Proposed API Endpoints

```
POST   /api/v1/flight-releases          — create new release (creates FR-xxx number)
GET    /api/v1/flight-releases          — list releases (with status filter)
GET    /api/v1/flight-releases/:id      — get release detail with all sections
PATCH  /api/v1/flight-releases/:id      — update release (creates amendment trail)
POST   /api/v1/flight-releases/:id/sign — sign (PIC or dispatcher signature)
GET    /api/v1/flight-releases/:id/pdf  — generate/download PDF
POST   /api/v1/flight-releases/:id/amend — create amendment from current release
```

## Views (Frontend)

1. **Release Dashboard** (`/dispatch`) — list of all flight releases, filterable by status/date/aircraft
2. **Release Detail** (`/dispatch/release/:id`) — the full release form shown above, editable when in DRAFT, read-only after RELEASED
3. **New Release** (`/dispatch/new`) — blank form wizard (or single-page form, TBD)

---

*This document is a living scope — it will change as we build and learn.*
