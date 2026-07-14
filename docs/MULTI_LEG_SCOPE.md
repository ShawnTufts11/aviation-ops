# Multi-Leg Mission Planning — Design Scope

## 1. What We're Building

A **mission-based flight planning system** that replaces single-flight scheduling with full multi-leg mission planning. A mission is a complete trip from origin back to base (or to final destination), consisting of one or more legs.

**Example Mission (Nassau → Haiti → Puerto Plata → Nassau):**
```
Leg 1: MYNN → MTPP   28 pax, 800kg cargo   C6-BT67
Leg 2: MTPP → MDPP   14 pax, 400kg cargo   (same aircraft)
Leg 3: MDPP → MYNN   12 pax, 200kg cargo   (same aircraft)
```
One mission, three legs, one aircraft, one crew — each leg with its own manifest.

---

## 2. Data Model

### Mission
```
Mission {
  id: UUID
  organization_id: UUID
  aircraft_id: UUID
  status: enum(draft, active, completed, cancelled)
  pilot_in_command: UUID (crew)
  second_in_command: UUID? (crew)
  mission_date: date
  total_flight_time: float (calculated from legs)
  total_fuel_burned: float (calculated from legs)
  notes: text?
  created_at, updated_at
}
```

### Flight Leg (replaces single Flight)
```
FlightLeg {
  id: UUID
  mission_id: UUID (FK → Mission)
  leg_number: int (1, 2, 3...)
  
  // Route
  departure_airport: string (ICAO)
  arrival_airport: string (ICAO)
  alternate_airport: string?
  
  // Times
  scheduled_departure: datetime
  scheduled_arrival: datetime
  actual_departure: datetime?
  actual_arrival: datetime?
  flight_time_minutes: int?
  
  // Manifest
  passengers: int
  cargo_weight_kg: float?
  fuel_on_board_liters: float?
  
  // Status
  status: enum(scheduled, active, completed, cancelled, diverted)
  
  // Compliance
  customs_clearance_ref: string?
  manifest_ref: string?
  
  notes: text?
  created_at, updated_at
}
```

### Manifest (Passenger-Level)
```
ManifestEntry {
  id: UUID
  leg_id: UUID (FK → FlightLeg)
  type: enum(passenger, crew, cargo)
  
  // Passenger details
  full_name: string
  date_of_birth: date
  gender: string
  nationality: string (ISO country code)
  passport_number: string?
  passport_expiry: date?
  id_number: string? (domestic)
  weight_kg: float (REQUIRED — for W&B)
  
  // Leg tracking
  boarding_leg_number: int (which leg they get on)
  deplaning_leg_number: int (which leg they get off)
  requires_passport: boolean (auto-calculated from route)
  
  // Cargo
  description: string?
  hazardous: boolean
  special_handling: string?
}
```

### Home Base Logic
- Organization has a `home_airport` field (default: MYNN)
- Missions flagged as "out-and-back" — system tracks if aircraft returns to base
- Warning if aircraft will be away from base when maintenance becomes due
- Crew rest requirements calculated based on time away from base

## 3. Auto-Population Logic

### Departure Chain
- Leg 1: departure defaults to home base (MYNN)
- Leg 2+: departure auto-fills from previous leg's arrival
- User can override for positioning/ferry legs

### Maintenance Catch-Up Warning
- System checks: "If aircraft departs on this mission and does NOT return to base by {date}, maintenance task '{title}' will become overdue"
- Suggests completing maintenance before departure or routing through a base with mx capability

---

## 3. Auto-Population Logic

### Departure Airport Chain
- **Leg 1:** User selects departure + arrival
- **Leg 2+:** Departure auto-fills from previous leg's arrival
- User can override departure if deadhead/positioning

### Manifest Carry-Forward
- **Leg 1:** User enters manifest (passengers + cargo)
- **Leg 2+:** Previous leg's manifest is pre-populated
- User adds/removes passengers and cargo per leg
- System tracks where each passenger boarded and deplaned

### Crew Carry-Forward
- Crew assigned at mission level (applies to all legs)
- Duty time calculated across ALL legs
- Warning if any single leg or cumulative time exceeds FAR 135 limits

---

## 4. Leg Warnings (Pre-Flight Checks Per Leg)

Each leg runs through the ops-check system before the mission can be activated:

### 4a. Range Capability
- Aircraft range vs leg distance (with 75% safe-range rule)
- Warning: "Requires fuel stop at ABC — {distance}nm exceeds safe range of {range}nm"
- Auto-suggest fuel stop as additional leg

### 4b. Weight & Balance
- Payload (pax + cargo) vs aircraft max payload
- Fuel load + payload vs MTOW
- Warning: "Over MTOW by {weight}kg — reduce fuel, pax, or cargo"

### 4c. Runway Length
- Aircraft takeoff/landing distance at MTOW vs destination runway length
- Requires airport database with runway data (Phase 2)

### 4d. NOTAMs
- Check destination airport for active NOTAMs
- Warning: "Runway 14/32 CLOSED at MTPP — verify alternates"
- Uses free NOTAM API (or manual entry in Phase 1)

### 4e. Passport / Customs
- Check if destination country differs from departure
- Flag: "MTPP (Haiti) requires passport — verify all passengers have valid passports"
- Flag: "US Customs pre-clearance required for MYNN→MTPP→US routing"

### 4f. Weather
- Live METAR at departure + arrival airports
- IFR/MVFR/VFR conditions flag

### 4g. Crew Duty Time (FAR 135.267/271)
- Flight time for this leg + cumulative mission time
- 8-hour limit (single pilot) / 10-hour (two pilots)
- Warning: "Adding this leg exceeds 10-hour duty limit — requires additional crew"

### 4h. Maintenance Conflicts
- Aircraft has open/overdue maintenance items
- Same check as current pre-flight system

---

## 5. User Flow

```
┌──────────────────────────────────────────────────────────────┐
│  CREATE MISSION                                                │
│                                                                │
│  Step 1: Select aircraft + crew (PIC/SIC)                      │
│  Step 2: Add legs (one at a time):                             │
│    → Select arrival airport (departure auto-filled)            │
│    → Set scheduled times                                       │
│    → Set manifest (passengers, cargo)                          │
│    → View leg warnings (range, weather, NOTAMs, customs)       │
│    → Add another leg or finish                                 │
│  Step 3: Review full mission:                                  │
│    → All legs listed with manifest, times, warnings            │
│    → Total flight time, total fuel                              │
│    → Crew duty time check                                       │
│  Step 4: Dispatch / Save as draft                              │
│                                                                │
│  During flight:                                                │
│    → Crew marks each leg active/completed                      │
│    → Manifest can be updated per leg                           │
│    → Auto-creates financial entries per leg on completion       │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Backend API Design

```
POST   /api/v1/missions                    — Create mission shell (aircraft + crew)
GET    /api/v1/missions                    — List missions (filter by status, date)
GET    /api/v1/missions/{id}               — Mission detail with all legs
PATCH  /api/v1/missions/{id}               — Update mission (status, crew)
DELETE /api/v1/missions/{id}               — Delete mission (draft only)

POST   /api/v1/missions/{id}/legs          — Add a leg to a mission
GET    /api/v1/missions/{id}/legs           — List legs in order
PATCH  /api/v1/missions/{id}/legs/{leg_id} — Update leg (times, manifest, status)

POST   /api/v1/missions/{id}/legs/{leg_id}/manifest — Add manifest entry
GET    /api/v1/missions/{id}/legs/{leg_id}/manifest  — Get manifest for leg

GET    /api/v1/missions/{id}/preflight     — Run all pre-flight checks on entire mission
GET    /api/v1/missions/{id}/legs/{leg_id}/preflight — Run checks on single leg
```

---

## 7. Frontend Components

### MissionListPage
- Table/list of missions with status, date, route summary
- Create new mission button → opens MissionBuilder

### MissionBuilder (wizard/multi-step)
- Step 1: Select aircraft + crew
- Step 2: Build legs (dynamic list — add/remove/reorder)
- Step 3: Review + pre-flight warnings

### LegEditor (inline in MissionBuilder)
- Arrival airport (departure auto-filled)
- Scheduled times
- Manifest editor (add/remove passengers, cargo)
- Real-time warnings panel

### MissionDetailPage
- Mission overview card
- Leg timeline with status
- Crew duty time tracker
- Per-leg manifest viewer

---

## 8. Phased Build Plan

### Phase 1 (MVP — this sprint)
- Mission + FlightLeg models
- Basic CRUD endpoints (create mission, add legs, set manifest)
- Auto-populate departure from previous leg arrival
- Per-leg manifest with passenger add/remove
- Pre-flight warnings: range, maintenance conflicts, weather
- Frontend: MissionBuilder wizard, MissionList

### Phase 2 (Next)
- Crew duty time tracking across multi-leg missions
- Weight & balance calculator
- Customs/passport flagging per country

### Phase 3 (Future)
- Airport database with runway lengths
- NOTAM integration
- Fuel planning with fuel stop suggestions
- Manifest PDF generation for customs

---

## 9. Fuel & Aircraft Profiles

### Aircraft Fuel Profile
Each aircraft gets a configurable fuel profile:
```
AircraftFuelProfile {
  cruise_burn_lph: float (liters per hour at cruise)
  climb_burn_lph: float (higher during climb)
  descent_burn_lph: float (lower during descent)
  taxi_burn_lph: float
  reserve_minutes: int (default: 45 min FAR 135 reserve)
  alternate_burn_lph: float (burn to alternate + reserve)
}
```
- Default profiles created per aircraft type during seed
- User can override per-mission based on current aircraft state or desired profile
- Fuel calculation: `leg_distance_nm / cruise_speed_kt × cruise_burn_lph + reserves`

### Manual Override
- Mission planner can enter custom fuel amount per leg
- System compares: fuel_on_board vs fuel_required
- Warning if fuel_on_board < fuel_required

## 10. NOTAMs (Phase 1 — Manual)
- Text field per leg for known NOTAMs
- Pilot/planner enters NOTAMs they've checked
- Phase 2: Automated NOTAM retrieval

## 11. Questions for You (Scope Gaps)

Before I start building, I need to nail down:

**A. Crew assignment**
- One crew for the whole mission (same pilots all legs)?
- Or can crew swap mid-mission (e.g., PIC changes at a stop)?

**B. Same-aircraft rule**
- Does a mission always use ONE aircraft across all legs?
- Or could cargo change to a different aircraft mid-mission?

**C. Manifest detail**
- For "passenger with passport" — do you need name-level tracking per passenger?
- Or just a count of passengers + a flag for "requires passport"?
- Same for cargo — just weight, or itemized list?

**D. Mission vs current flight system**
- Do we replace the current single-flight creation with missions?
- Or keep both (quick single-leg flights vs multi-leg missions)?

**E. NOTAMs**
- Phase 1: manual entry (text field per leg)?
- Phase 2: automated via free NOTAM API?

**F. Fuel planning**
- Do you need automatic fuel burn calculations based on leg distance + aircraft type?
- Or just manual fuel entry per leg?

---

This is a significant build — roughly equivalent to building a new module. Once you answer the questions above, I'll scope the effort in days and we'll build it phase by phase.
