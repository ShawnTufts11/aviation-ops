#!/usr/bin/env python3
"""SDVOSB Opportunity Scanner v1 — SAM.gov API + relevance scoring for ParaRig."""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────
def _load_env(path: str):
    """Load a .env file manually (no external deps needed)."""
    p = Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

_load_env(os.path.expanduser("~/.hermes/.env"))

SAM_API_KEY = os.getenv("SAM_API_KEY", "")
OUTPUT_DIR = Path(__file__).resolve().parent
RESULTS_FILE = OUTPUT_DIR / "results.json"

# ParaRig's capability profile — tight scoring for software/logistics/training
PARARIG_PROFILE = {
    "naics_core": ["541511", "541512", "541519"],         # Software dev + IT services
    "naics_related": ["541330", "611420", "541990"],      # Engineering, training, consulting
    "psc_core": ["D", "R", "U", "7A"],                    # IT, R&D, training, IT svcs
    "keywords_high": [
        "software", "logistics", "tracking", "training", "readiness",
        "data", "dashboard", "api", "web application", "supply chain",
        "maintenance management", "inspection", "compliance", "aviation",
    ],
    "keywords_penalty": [
        "fire alarm", "fire suppression", "plumbing", "hvac", "electrical",
        "construction", "janitorial", "roofing", "painting", "elevator",
        "generator", "concrete", "asphalt", "landscaping", "snow removal",
        "hazardous waste", "asbestos", "pest control", "sewer", "dumpster",
    ],
    "agencies": ["DEPT OF DEFENSE", "DEPT OF THE ARMY", "DEPT OF THE NAVY",
                  "DEPT OF THE AIR FORCE", "VETERANS AFFAIRS",
                  "HOMELAND SECURITY", "NASA"],
}

# Vehicle/eligibility gates that make an opportunity UNBIDDABLE without the
# right contract vehicle (MAC, IDIQ, GWAC, BPA, GSA Schedule, etc.). The v2
# API does NOT return description text (noticedesc endpoint 404s), so these
# patterns can only be checked against title/agency/set-aside text — which
# usually misses. Hence: any HIGH-SCORE record gets `verifyBeforePursue` so a
# human confirms eligibility on SAM.gov before investing time.
GATE_PATTERNS = [
    "seaport", "mac holder", "multiple award", "idiq", "gwac", "bpa",
    "schedule holder", "gsa schedule", "task order", "fair opportunity",
    "only those contractors", "no other offers will be considered",
]

# Word-boundary aware (Aug 12, 2026): raw substring matching let "bpa" match
# inside "subpart" (FAR Subpart 12.6 boilerplate) and false-flag ordinary
# combined synopses as vehicle-gated. \b...\b keeps single-token patterns
# honest while multi-word phrases are unaffected.
_GATE_RX = [re.compile(r"\b" + re.escape(p) + r"\b", re.I) for p in GATE_PATTERNS]

# Hard-exclude patterns — unambiguous never-ParaRig work. Keeps the board
# clean at the source so users aren't dismissing the same junk every scan.
NSN_PARTS_RE = re.compile(r"^\d{2,4}--")
AERIAL_HARDWARE_KW = ("sling", "parachute", "webbing", "harness", "riser",
                      "canopy", "cargo net", "restraint", "tie-down",
                      "tiedown", "airdrop")
CONSTRUCTION_PREFIX_RE = re.compile(
    r"^(Y1DA|Y1DZ|Y1NE|Z2DA|Z2DZ|Z1DA|Z--|C1DA|N055|N091|Y1[0-9A-Z]|Z[0-9A-Z]?)--"
)
JUNK_TITLE_KW = [
    "janitorial", "pest control", "fire alarm", "fire guard", "sprinkler",
    "herbicide", "grounds maintenance", "landscaping", "security coverage",
    "security officer", "telephone operator", "switchboard", "food service",
    "dining", "boiler", "generator", "electrical", "seismic", "retrofit",
    "water storage", "bridge crane", "replace windows", "dishwasher",
    "canteen", "parking", "mold remediation", "drop ceiling", "steam line",
    "flooring", "topsoil", "dental", "amalgam", "reprocessing", "vacuum sealer",
    "wayfinding", "cogeneration", "police dispatch", "water testing",
    "cooling coil", "awning", "cart storage", "rideshare", "sports official",
    "aerobics", "thyroid", "telesitter", "stress test", "ultrasonic washer",
    "clinical support", "biomed", "fuel filtering", "fuel oil tank",
    "storage container", "conex container", "moving, storage", "bulk retail",
    "fuel storage", "direct tv", "greenspace", "maneuver lane", "sunshade",
    "radio trunking", "cancellation of combined", "observation unit",
    "primary care", "repair building", "warehouse as a service", "smartpump",
    "vocera", "verafit", "lawn blower", "furniture", "refrigerator",
    "batteries", "ultrasound", "defibrillator", "pressure sensitive",
    "switch,", "valve,", "handle,", "coupling half", "handset",
    "packing with", "accessories stowag", "filter element", "fans", "oven",
    "three bay", "replacement bldg", "replace steam", "correct safety",
    "emergency generators", "combustion", "water storage facility",
]


def is_junk_title(title: str) -> bool:
    """Return True if the title is unambiguous never-ParaRig work."""
    t = (title or "").strip()
    tl = t.lower()
    if NSN_PARTS_RE.match(t):
        # Keep in-lane aerial-delivery hardware (slings, webbing, etc.)
        return not any(k in tl for k in AERIAL_HARDWARE_KW)
    if CONSTRUCTION_PREFIX_RE.match(t):
        return True
    return any(k in tl for k in JUNK_TITLE_KW)


def score_opportunity(opp: dict) -> int:
    """Score 0-100 how well this matches ParaRig's software/logistics capabilities."""
    score = 0
    title = str(opp.get("title", "")).lower()
    text = json.dumps(opp).lower()
    agency = str(opp.get("fullParentPathName", "")).lower()
    naics = str(opp.get("naicsCode", "")).strip()
    psc = str(opp.get("classificationCode", "")).strip()

    # NAICS core match (+30)
    if naics in PARARIG_PROFILE["naics_core"]:
        score += 30

    # NAICS related match (+15)
    elif naics in PARARIG_PROFILE["naics_related"]:
        score += 15

    # PSC code match (+15)
    for code in PARARIG_PROFILE["psc_core"]:
        if psc.startswith(code):
            score += 15
            break

    # Title keyword match (+15 each, no cap — title tells the story)
    for kw in PARARIG_PROFILE["keywords_high"]:
        if kw in title:
            score += 15

    # Body keyword density (up to +15)
    body_matches = sum(1 for kw in PARARIG_PROFILE["keywords_high"] if kw in text)
    score += min(body_matches * 3, 15)

    # Agency match (+5)
    for a in PARARIG_PROFILE["agencies"]:
        if a.lower() in agency:
            score += 5
            break

    # Penalty for construction/maintenance garbage (-20)
    for kw in PARARIG_PROFILE["keywords_penalty"]:
        if kw in title or kw in text:
            score -= 20
            break

    # Recent posting bonus (+10)
    posted = opp.get("postedDate", "")
    if posted:
        try:
            posted_dt = datetime.strptime(posted.split(" ")[0], "%Y-%m-%d")
            if (datetime.now() - posted_dt).days <= 7:
                score += 10
        except ValueError:
            pass

    return max(min(score, 100), 0)


def detect_vehicle_gate(opp: dict) -> dict:
    """Detect eligibility/vehicle gates from the text the API actually returns.

    Returns {"vehicleGate": "suspected"|"unknown", "gateMatched": str|""}.
    The v2 API omits description text, so absence of a match is NOT proof of
    eligibility — hence "unknown", never "none".
    """
    haystack = " ".join(str(opp.get(k, "")) for k in
                        ("title", "solicitationNumber", "fullParentPathName",
                         "typeOfSetAsideDescription", "typeOfSetAside",
                         "type", "baseType")).lower()
    for rx in _GATE_RX:
        m = rx.search(haystack)
        if m:
            return {"vehicleGate": "suspected", "gateMatched": m.group(0)}
    return {"vehicleGate": "unknown", "gateMatched": ""}


def classify_biddability(opp: dict, gate: dict) -> dict:
    """Feasibility read from title/type/agency text (no description needed).

    Returns {"bidable": bool, "bidClass": str, "bidBlockReason": str}.
    bidClass values:
      OPEN         — open competition, bid it
      SOLE_INTENT  — FAR 5.7 notice: contract is going to one company; only a
                     capability-challenge window exists (not an open bid)
      SOURCES_SOUGHT — market research; respond to express interest only
      AWARD        — award already granted (defensive)
      GATED        — vehicle gate (MAC/IDIQ/GWAC/BPA...) suspected from text
      UNKNOWN      — Special Notice with no clear signal; check SAM.gov
    """
    title = str(opp.get("title", ""))
    tl = title.lower()
    opp_type = str(opp.get("type", opp.get("baseType", ""))).strip().lower()
    reason = ""
    bid_class = "OPEN"

    if re.search(r"intent to sole source|notice of intent", tl):
        bid_class = "SOLE_INTENT"
        reason = ("Sole-source intent — contract direction is set; only a "
                  "15-day capability-challenge window applies")
    elif opp_type == "sources sought":
        bid_class = "SOURCES_SOUGHT"
        reason = "Market research only — respond to express interest; no award from this notice"
    elif opp_type in ("award notice", "award"):
        bid_class = "AWARD"
        reason = "Award already granted — not biddable"
    elif gate.get("vehicleGate") == "suspected":
        bid_class = "GATED"
        reason = (f"Vehicle gate suspected ({gate.get('gateMatched')}) — "
                  "verify on SAM.gov before investing time")
    elif opp_type == "special notice":
        bid_class = "UNKNOWN"
        reason = "Special notice — an announcement, not an open solicitation; check SAM.gov for what it is"

    return {
        "bidable": bid_class == "OPEN",
        "bidClass": bid_class,
        "bidBlockReason": reason,
    }


def fetch_sam_opportunities(days_back: int = 30, limit: int = 100) -> list:
    """Fetch SDVOSB set-aside AND sole-source opportunities from SAM.gov API."""
    if not SAM_API_KEY:
        print("WARN: SAM_API_KEY not set — no data")
        return []

    posted_from = (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y")
    posted_to = datetime.now().strftime("%m/%d/%Y")

    all_opps = []
    for set_aside in ["SDVOSBC", "SDVOSBS"]:
        params = {
            "api_key": SAM_API_KEY,
            "limit": str(limit),
            "typeOfSetAside": set_aside,
            "postedFrom": posted_from,
            "postedTo": posted_to,
        }
        url = "https://api.sam.gov/opportunities/v2/search?" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode()
                if raw.strip() == "No match found!" or not raw.strip():
                    continue
                data = json.loads(raw)
                opps = data.get("opportunitiesData", [])
                all_opps.extend(opps)
                print(f"  {set_aside}: {len(opps)} opportunities (total in DB: {data.get('totalRecords', 0)})")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  {set_aside}: HTTP {e.code} — {body[:100]}")
        except Exception as e:
            print(f"  {set_aside}: error — {e}")

    return all_opps


def run_scan() -> dict:
    """Execute a full scan and return results with metadata."""
    opportunities = fetch_sam_opportunities(days_back=30, limit=100)

    scored = []
    for opp in opportunities:
        # Award Notices are past awards — NOT biddable. They clutter the hot
        # list (logistics/VA keywords score them high). Exclude at the source.
        opp_type = str(opp.get("type", opp.get("baseType", ""))).strip().lower()
        if opp_type == "award notice" or opp_type == "award":
            continue
        # Junk titles (NSN parts, construction, facility ops) — never ParaRig
        # work. Exclude so the board stays clean without manual dismissal.
        if is_junk_title(opp.get("title", "")):
            continue
        score = score_opportunity(opp)
        gate = detect_vehicle_gate(opp)
        bid = classify_biddability(opp, gate)
        sam_url = opp.get('uiLink', '') or f"https://sam.gov/workspace/contract/opp/{opp.get('noticeId', '')}/view"
        deadline = opp.get('responseDeadLine', opp.get('reponseDeadLine', ''))
        if deadline and 'T' in str(deadline):
            try:
                deadline = deadline.split('T')[0]
            except:
                pass
        scored.append({
            "title": opp.get("title", "Untitled"),
            "noticeId": opp.get("noticeId", ""),
            "solicitationNumber": opp.get("solicitationNumber", ""),
            "naicsCode": opp.get("naicsCode", ""),
            "classificationCode": opp.get("classificationCode", ""),
            "agency": opp.get("fullParentPathName", opp.get("department", "")),
            "postedDate": opp.get("postedDate", ""),
            "responseDeadLine": deadline,
            "type": opp.get("type", opp.get("baseType", "")),
            "setAside": opp.get("typeOfSetAsideDescription", ""),
            "setAsideCode": opp.get("typeOfSetAside", ""),
            "description": "",
            "url": sam_url,
            "relevanceScore": score,
            "vehicleGate": gate["vehicleGate"],
            "gateMatched": gate["gateMatched"],
            # Feasibility read — title/type-based; enrichment upgrades GATED to
            # confirmed via the SAM.gov description (see enrich_hot_leads.py).
            "bidable": bid["bidable"],
            "bidClass": bid["bidClass"],
            "bidBlockReason": bid["bidBlockReason"],
            # Descriptions aren't available via API — a high score alone is not
            # enough to pursue. Human must confirm eligibility on SAM.gov.
            "verifyBeforePursue": score >= 50,
        })

    scored.sort(key=lambda x: x["relevanceScore"], reverse=True)

    result = {
        "scanTimestamp": datetime.now().isoformat(),
        "totalOpportunities": len(scored),
        "dataSource": "sam_gov_api",
        "pararigProfile": PARARIG_PROFILE,
        "opportunities": scored,
    }
    return result


def main():
    print("SDVOSB Opportunity Scanner v1")
    print("=" * 50)
    print(f"API Key: {'SET' if SAM_API_KEY else 'NOT SET'}")
    print()

    result = run_scan()
    RESULTS_FILE.write_text(json.dumps(result, indent=2))
    print(f"Results saved to {RESULTS_FILE}")
    print(f"Found {result['totalOpportunities']} SDVOSB opportunities")

    top = [o for o in result["opportunities"] if o["relevanceScore"] >= 30]
    if top:
        print(f"\nWorth a look (score >= 30): {len(top)}")
        for opp in top:
            flag = ""
            if opp.get("verifyBeforePursue"):
                flag = "  [VERIFY VEHICLE GATE ON SAM.GOV]"
            elif opp.get("vehicleGate") == "suspected":
                flag = f"  [GATE: {opp.get('gateMatched', '')}]"
            print(f"  [{opp['relevanceScore']}/100] {opp['title'][:70]}{flag}")
            print(f"         {opp['agency'][:60]}")
            print(f"         Due: {opp['responseDeadLine']}")
    else:
        print("\nNo high-relevance matches found (score >= 50)")

    mc_dir = Path(os.path.expanduser("~/ai-infra/MissionControl/sdvosb"))
    mc_dir.mkdir(parents=True, exist_ok=True)
    (mc_dir / "results.json").write_text(json.dumps(result, indent=2))
    print(f"\nSynced to MC dashboard")


if __name__ == "__main__":
    main()
