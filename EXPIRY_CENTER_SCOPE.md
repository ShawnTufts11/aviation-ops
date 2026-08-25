# Expiry Center / Compliance Hub — Integration Scope

**Date:** 2026-08-25
**Status:** SCOPED — awaiting approval (no build started)
**Branch target:** develop

## 1. Executive Summary

The aviation-ops suite already stores ~90% of the data a compliance/expiry
product needs. The easiest path is NOT a new module — it is a read-only
aggregation endpoint over existing tables, a Discord watchdog cron (reusing
the loyalty-expiry-monitor pattern), and a frontend extension of the existing
Compliance page. Phases 1–3 require **zero schema changes and zero
migrations**. The only genuinely new engineering is Phase 4: computing FAA
pilot currency from the logbook instead of storing stale snapshots.

## 2. What Already Exists (inventory, verified 2026-08-25)

| Source | Table(s) | Expiry/currency data | Where surfaced today |
|--------|----------|----------------------|----------------------|
| Aircraft | `aircraft` | registration_expiry, airworthiness_expiry, coa_expiry, insurance_expiry | Fleet page (partial) |
| Aircraft components | `aircraft_components` | tbo_calendar_days, tbo_hours, life_limit_* | Aircraft detail |
| Crew | `crew_members` | license_expiry, medical_expiry, passport_expiry, last_proficiency_date | Crew page (color-coded quals) |
| Crew quals | `crew_qualifications` | issued_date, expiry_date, status (current/expiring_soon/expired) | Crew page |
| Documents | `documents` | expiry_date, reminder_days, status, countries, regulations | Compliance page + briefing card |
| AD/SB | `ad_compliance.py` service | compliance %, overdue, due-soon, grounded-on-critical | Aircraft detail endpoint |
| Logbook | `pilot_log_entries` | auto-populated from completed flights; live 90-day hours summary | `/api/v1/logbook/crew/{id}/summary` |

**Key finding:** the crew currency snapshot fields (`last_90d_hours`,
`last_90d_landings`, `last_12m_hours`, `last_flight_date`,
`last_proficiency_date`) exist but are ONLY written by seed scripts — nothing
computes them from the logbook at runtime. That is the one real gap.

## 3. The Gap

1. **No unified view.** `GET /api/v1/compliance/dashboard` covers Documents
   only. Briefing `compliance_snapshot` card = document counts only. Aircraft
   insurance/registration, crew medical/license/passport, quals, ADs, and
   component TBOs are scattered across 5+ endpoints.
2. **No computed pilot currency.** FAA rules (90-day/3-landing day currency,
   6-month instrument, 24-month flight review) are not derived from the
   logbook; the snapshot fields are seeded, not computed.
3. **No proactive alerting.** Nothing tells the DoO "insurance expires in
   12 days" until someone opens a page.

## 4. Proposed Build — Phased, Easiest First

### Phase 1 — Expiry Center API (½ day, no migration)
New read-only endpoint: `GET /api/v1/compliance/expiry-center`
- Pulls all sources: aircraft expiries + component calendar limits, crew
  license/medical/passport, quals, documents, AD due-soons.
- Returns: `expiring` (within configurable window, default 30d), `expired`,
  per-source counts, each item with `days_left`, source, entity name/tail,
  and a `reminder_days` hint.
- Role-gated: read = org membership (consistent with existing compliance
  list); full detail stays DoO+ per existing matrix.
- Pattern: reuse `DocumentResponse.model_validate(d).model_dump()` — avoid
  hand-written dict serializers (known 500-drift pitfall).
- Verify with curl before any frontend work (API-first rule).

### Phase 2 — Compliance Watch Discord cron (1–2 hrs)
- Clone `~/.hermes/scripts/loyalty-expiry-monitor.py` watchdog pattern:
  no-agent cron, silent when healthy, alert only on expiring/expired.
- Script queries the Phase-1 endpoint (or the DB directly with a read-only
  helper), emits one line per at-risk item with the fix hint.
- Schedule daily 08:15, deliver `discord:#command-center` (same as Update
  Watch / Loyalty Watch).
- Immediate internal value; also demonstrates the alerting story for
  prospective 135 customers.

### Phase 3 — Frontend: Compliance page becomes Expiry Center (1 day)
- Extend existing `CompliancePage.tsx` (don't create a new page): add
  Aircraft / Crew / Quals sections to the dashboard tab, unified "expiring
  next 30/60/90d" list with color-coded days-left badges (existing status
  color scheme), click-through to existing detail pages.
- Reuses existing ui components (Badge, Card, Tabs, Dialog).

### Phase 4 — Pilot Currency Service (1–2 days, the differentiator)
- New service `backend/app/services/currency.py`: compute FAA currency live
  from `pilot_log_entries`:
  - 90-day: ≥3 day landings in trailing 90 days (needs `day_landings` —
    exists in logbook)
  - 24-month: flight review/proficiency from `crew_qualifications`
    (proficiency_check / recurrent_training expiry) or
    `last_proficiency_date`
  - 6-month instrument: needs approach counts — logbook has
    `instrument_time` but not per-approach counts; mark as "needs data"
    until approach logging is added (honest limitation, do not fake it)
  - Medical/license/passport: straight date checks (already in crew table)
- Wire into `GET /api/v1/logbook/crew/{id}/summary` and the crew card.
- Optional write-back: update the snapshot fields on mission completion
  (verify existing mission-complete → logbook hook first; only add if the
  hook exists — otherwise leave snapshots read-only).

### Phase 5 — Productization (later, only if we sell it)
- PDF "Compliance Report" export (audit-ready, per-aircraft + per-crew),
  configurable reminder windows per doc type, per-country regs filtering.
- This is the thing a 135 operator writes a check for. Not in scope now.

## 5. Effort & Sequence

| Phase | Deliverable | Effort | Depends on |
|-------|------------|--------|------------|
| 1 | expiry-center API | ½ day | — |
| 2 | Discord Compliance Watch | 1–2 hrs | Phase 1 |
| 3 | Compliance page extension | 1 day | Phase 1 |
| 4 | currency service | 1–2 days | Phase 1; verify logbook hook |
| 5 | productized report export | later | 3–4 |

Total to first usable value (Phases 1–2): ~1 day. Full internal tool: ~3 days.

## 6. Risks & Pitfalls (from the ops skill — plan for them)

- **Serializer drift:** use `model_validate().model_dump()` everywhere; never
  hand-write `_to_dict()` for new endpoints (500s otherwise).
- **SQLite migrations:** none needed for Phases 1–3 (no schema change). If
  Phase 4 adds columns: batch_alter_table for enum changes; `server_default`
  for NOT NULL booleans.
- **RBAC:** keep read at org-membership; write (doc create/update) stays
  AE/DoO; PII fields (passport) masked per `_redact()` convention if exposed.
- **AD due-soon:** reuse `ad_compliance.py` — do not re-implement; call it.
- **Post-session docs:** every build session ends with README + SPEC update
  on develop (hard rule) + FEATURE_BACKLOG status flip.
- **Currency honesty:** instrument currency needs approach counts we don't
  log; ship 90-day + 24-month + dates first, mark instrument as data-gap
  rather than inventing a rule.

## 7. Open Questions for Discussion

1. Alert window: 30/60/90 days before expiry for the Discord watch? (Proposal:
   30d default, 60d for medical/insurance, 90d for passport — per-item
   reminder_days already exists in Document model.)
2. Does Phase 4 need the snapshot write-back on flight completion, or is a
   live-computed read (no write) enough? (Proposal: live read first; write-back
   only if the mission-complete hook already creates logbook entries — verify.)
3. Should the Expiry Center be gated DoO+ only, or visible to all roles with
   write gated? (Proposal: read for all org members, matches existing
   compliance list.)
4. Product framing: sell as part of the ops suite (recommended) vs standalone
   compliance tool.
