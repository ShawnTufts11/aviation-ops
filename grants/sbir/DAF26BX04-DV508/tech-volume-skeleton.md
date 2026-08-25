# DAF26BX04-DV508 — SBIR Phase I Technical Volume (SKELETON)

**Topic:** Advancing Assured Access: Integrated Digital Capabilities for the 2 SLS to Accelerate Mission Tempo and Readiness
**Solicitation:** DoD SBIR 2026 BAA (USAF)
**Close Date:** **2026-08-19** (VERIFY on DSIP portal — https://www.dodsbirsttr.mil/submissions)
**Phase I:** ~$75K, 3 months, feasibility study
**Company:** ParaRig Dynamics LLC (SDVOSB, SAM.gov active, UEI + CAGE on file)
**PI:** Shawn Tufts — FAA Master Rigger, 20+ yrs NSW/SWCC/EOD, Air Ops Trainer/Examiner
**Status:** SKELETON v0.1 — 2026-08-14. Needs: review, verify topic text against portal, PDF render (5-page limit), portal submission.

---

## 1. Technical Abstract (~1,500 chars, public-safe)

ParaRig Dynamics proposes Mission Ops Readiness (MOR) — a commercial-derived, integrated digital operations platform that accelerates spaceport mission tempo by unifying scheduling, readiness tracking, knowledge management, and decision support for the 2nd Space Launch Squadron. MOR is built on ParaRig's proven Part 135 aviation operations backbone (route planning, crew/equipment readiness, weather integration, role-based access, maintenance control), already validated end-to-end in commercial flight operations with a 6-leg, 3,554nm Caribbean mission loop, live FAA METAR/NOTAM feeds, FAR 135.267 crew-duty enforcement, and a 3-gate release workflow (maintenance → PIC → dispatch).

The Phase I effort adapts and extends this platform to spaceport operations: intelligent schedule assistance that detects conflicts and slack across launch windows and ground crews; centralized mission information management replacing siloed spreadsheets and email; rapid search and retrieval of historical mission data for training and post-mission analysis; and role-gated dashboards that surface readiness status at a glance. Phase I delivers a spaceport-configured prototype with representative 2 SLS mission data, a validated workflow model with two demonstration scenarios, and a commercialization roadmap. MOR is dual-use: the same platform serves commercial Part 135 operators, spaceport ground crews, and expeditionary airfield operations, aligning with AFWERX modernization priorities for readiness and decision quality.

## 2. Problem Statement

2 SLS mission operations face three compounding friction points: (1) **fragmented information** — schedules, crew qualifications, equipment status, and lessons-learned live in separate spreadsheets, emails, and memory; (2) **manual scheduling and coordination** — launch-window planning and crew assignment are done by hand, consuming senior NCO/Officer time and producing avoidable conflicts; (3) **slow readiness assessment** — leadership lacks a single view of personnel/equipment/ground-support readiness, so "are we ready for this window?" is answered slowly and inconsistently. The Air Force objective for this topic is integrated digital capability that demonstrably accelerates tempo and improves decision quality. Current commercial tools are either general-purpose project trackers (no domain workflow) or monolithic ERPs (too heavy, no mission model). ParaRig's MOR fills the gap with a lightweight, mission-native platform.

## 3. Technical Solution — Architecture

MOR reuses ParaRig's validated aviation ops architecture (FastAPI backend, React/MapLibre frontend, PostgreSQL, RBAC) and extends it with spaceport-specific modules:

| Topic requirement | MOR module (built) | Status |
|---|---|---|
| Intelligent scheduling assistance | Route/mission planner with constraint engine (duty-time, weather, aircraft/crew availability) | ✅ built (aviation) — extend to launch windows/ground crews |
| Centralized information management | Mission ops center: missions, releases, briefings, maintenance control, cost tracking | ✅ built — extend to spaceport entities |
| Advanced search / historical data | Knowledge management + searchable mission history, P&L and readiness rollups | ✅ built — extend with lessons-learned corpus |
| Reduced manual workload | 3-gate release workflow (maint → PIC → dispatch), bulk import, checklist automation | ✅ built — extend signoff model to spaceport ops |
| Better decision quality / readiness | Role-gated dashboards, weather (METAR/NOTAM), degraded-mode flags, alerting | ✅ built — add spaceport readiness board |

**Phase I delta work:** (a) spaceport data model (launch windows, ground crews, cert currency), (b) scheduling-assistant prototype with conflict detection over a representative 30-day 2 SLS ops calendar, (c) readiness scoreboard prototype, (d) two demonstration scenarios validated with mission data.

## 4. Phase I Work Plan (3 months, 4 tasks)

- **Task 1 (Wk 1-3):** Requirements validation — map MOR modules to 2 SLS workflows with feedback from operators; define spaceport data model and acceptance criteria.
- **Task 2 (Wk 2-6):** Prototype build — extend backend + frontend with spaceport entities, scheduling assistant, readiness scoreboard; seed with representative mission data.
- **Task 3 (Wk 6-10):** Demonstration — run two scenarios (rapid-turn launch window with conflicting crew certs; historical mission retrieval for training) capturing tempo/decision-time metrics vs baseline manual workflow.
- **Task 4 (Wk 10-12):** Commercialization plan + Phase II roadmap — transition strategy to USAF and commercial Part 135/spaceport markets; final report.

Success criteria: demonstrable reduction in scheduling-assistance time and readiness-assessment time vs baseline; operator-validated workflow; working prototype for Phase II.

## 5. Commercialization & Transition

Dual-use: commercial Part 135 charter operators (existing market, ParaRig platform already deployed there), spaceport ground ops (commercial spaceports), expeditionary airfields. Phase II path: productionize scheduling assistant with ML conflict prediction; integrate with AF enterprise data sources. ParaRig is SDVOSB (set-aside eligible) and retains commercial revenue from the aviation deployment, reducing government cost risk.

## 6. Team

**Shawn Tufts (PI)** — FAA Master Rigger; 20+ years NSW/SWCC/EOD; Air Operations Trainer/Examiner; jump/fastrope/CaAST ops; accident investigation; expert skydiver/tunnel coach; 28 years experience; software-defined ops platform architect (ParaRig Aviation Ops, 9/12 modules, 110+ backend routes, E2E-tested). PI time: 100%. Rate: $75/hr fully loaded (sole prop, no fringe; comparable GS-14/15).

## 7. Budget — $74,997 (Phase I, 3 months)

| Category | Amount |
|---|---|
| Direct Labor (PI, 400 hrs @ $75) | $30,000 |
| Subcontractor (AI/ML consultant, optional → fold into labor if portal blocks) | $20,000 |
| Equipment (prototype hardware/edge device) | $12,000 |
| Travel (GSA CONUS per diem, FL field) | $5,000 |
| Materials | $5,000 |
| Software (licenses) | $2,000 |
| Overhead (10% of labor) | $1,000 |
| **Total** | **$74,997** |

Profit 0% · Cost share $0 · ODC-Supplies: $1 token item if portal requires.

## 8. Certifications (single-member SDVOSB LLC)

Yes: PI 100% employed, R&D in US at offeror facilities, export-control compliant, SDVOSB disadvantaged, release to EDOs. No: federal facilities, ITAR/EAR data, human/animal subjects, foreign nationals, equivalent work elsewhere.

---

## SUBMISSION CHECKLIST (Aug 14 → Aug 19)

- [ ] **Verify topic text + close date on DSIP** (https://www.dodsbirsttr.mil/submissions) — skeleton built from secondary sources; confirm exact objective language and Q&A
- [ ] Fill proposal metadata: track=BAA, component=USAF, topic=DAF26BX04-DV508, title
- [ ] Volume I summary + keywords (8 max)
- [ ] Volume II Tech Volume → 5-page PDF (weasyprint HTML/CSS, 10pt, compact tables — ref afwerx-sbir-submission skill)
- [ ] Volume III Cost Volume (fields in portal order: labor → overhead 10% → G&A 0% → ODC materials/travel/other/equipment → supplies $1 → profit 0%)
- [ ] Certifications + disclosures
- [ ] Submit before Aug 19 EOD Eastern
- [ ] Also prep CSO (opens Aug 26) as backup track with same core content — Release 5 window
