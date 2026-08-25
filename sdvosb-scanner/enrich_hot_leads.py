#!/usr/bin/env python3
"""Enrich hot SDVOSB leads with full descriptions + vehicle-gate detection.

The SAM.gov v2 API returns titles only (noticedesc endpoint 404s), so hot
leads must be rendered in a real browser to read the Description section.
This script drives the system Chrome via Playwright (channel='chrome'),
extracts the description text and eligibility gates for the top-N leads,
and writes them back into results.json + the MC dashboard copy.

Usage:
    .venv/bin/python enrich_hot_leads.py [--top 5] [--min-score 40]

Requires: dedicated venv at ./venv... (this script's own dir .venv) with
`pip install playwright`, and google-chrome(-stable) on PATH.
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("playwright not installed in this venv — run: .venv/bin/pip install playwright")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scanner import GATE_PATTERNS  # reuse the gate vocabulary

# Word-boundary-aware compiled patterns (Aug 12, 2026): raw substring
# matching let "bpa" match inside "subpart" ("FAR Subpart 12.6" boilerplate)
# and false-flag ordinary combined synopses as vehicle-gated. \b...\b keeps
# single-token patterns honest ("bpa", "seaport", "idiq") while multi-word
# phrases ("mac holder", "no other offers will be considered") are unaffected.
_GATE_RX = {p: re.compile(r"\b" + re.escape(p) + r"\b") for p in GATE_PATTERNS}

OUTPUT_DIR = Path(__file__).resolve().parent
RESULTS_FILE = OUTPUT_DIR / "results.json"
MC_FILE = Path.home() / "ai-infra/MissionControl/sdvosb/results.json"
DISMISSED_FILE = Path.home() / "ai-infra/MissionControl/contracts/dismissed.json"


def load_dismissed() -> set:
    """Return dismissed noticeIds (board-level clutter control)."""
    try:
        return set(json.loads(DISMISSED_FILE.read_text()).get("noticeIds", []))
    except Exception:
        return set()

DESC_PATTERN = re.compile(
    r"DescriptionView Changes\s*\n(.*?)(?=\n\s*(?:Attachments/Links|Contact Information|History|Award Notices))",
    re.S,
)
# Fallback: any "Description" header — pick the match with the longest content
# (the nav tab bar also contains a bare "Description" label, which yields an
# empty/garbage capture; the longest capture is the real section).
DESC_FALLBACK = re.compile(
    r"Description\s*\n(.*?)(?=\n\s*(?:Attachments/Links|Contact Information|History|Award Notices))",
    re.S,
)


def detect_gates(text: str) -> tuple[str, str]:
    """Return (gate, matched_pattern) from rendered text.

    Bare pattern mentions are NOT gates — "follow-on contract of Seaport NxG
    task order" is historical context (false-positive trap, verified Aug 10:
    MCU CDET). Only gate phrasing counts: "MAC Holders only", "no other
    offers will be considered", "reserved for", etc.

    Word-boundary matching (Aug 12, 2026): GATE_PATTERNS are matched with
    \\b...\\b so "bpa" does NOT match inside "subpart" ("FAR Subpart 12.6"
    boilerplate appears in nearly every combined synopsis) and "seaport"
    doesn't match inside other words. Verified false positive: SCOS
    W31P4Q26RA002 was flagged GATED because 'bpa' matched "Subpart" and the
    window check saw "the only solicitation" — standard FAR 12.6 preamble.
    """
    hay = text.lower()
    strong = (
        "mac holders only", "no other offers will be considered",
        "reserved for only", "only those contractors", "eligible offerors are",
        "limited to holders", "open only to", "only for contractors",
        "restricted to holders",
    )
    if any(s in hay for s in strong):
        for pat, rx in _GATE_RX.items():
            if rx.search(hay):
                return "suspected", pat
        return "suspected", "restricted"
    for pat, rx in _GATE_RX.items():
        m = rx.search(hay)
        if m is None:
            continue
        window = hay[max(0, m.start() - 80):m.end() + 120]
        if any(w in window for w in ("only", "restricted", "limited", "reserved",
                                     "must be", "eligible", "exclusive")):
            return "suspected", pat
    return "unknown", ""


def extract_description(text: str) -> str:
    m = DESC_PATTERN.search(text)
    if not m:
        cands = list(DESC_FALLBACK.finditer(text))
        if not cands:
            return ""
        m = max(cands, key=lambda x: len(x.group(1)))
    desc = re.sub(r"\s+", " ", m.group(1)).strip()
    return desc[:2000]


def enrich(opps: list[dict], browser) -> list[dict]:
    page = browser.new_page(
        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/151.0 Safari/537.36")
    )
    for opp in opps:
        url = opp.get("url", "")
        opp["descriptionText"] = ""
        opp["descriptionEmpty"] = True
        opp["gateFound"] = ""
        opp["gateVerified"] = False
        if not url:
            continue
        try:
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)  # let Angular render
            body = page.inner_text("body")
            desc = extract_description(body)
            gate, matched = detect_gates(body)
            opp["descriptionText"] = desc
            opp["descriptionEmpty"] = len(desc) < 30
            opp["gateFound"] = matched
            opp["gateVerified"] = gate == "suspected"
            # A gate confirmed in the rendered description is stronger evidence
            # than the scanner's title-only suspicion: flip biddability now.
            if opp["gateVerified"]:
                opp["bidable"] = False
                opp["bidClass"] = "GATED"
                opp["bidBlockReason"] = (
                    f"Vehicle gate confirmed on SAM.gov ({matched}) — "
                    "eligibility restricted to holders")
            # The description can also PROVE sole-source intent when the title
            # is vague (Special Notices often bury it: "NOTICE OF INTENT TO
            # AWARD SOLE SOURCE ... awarded to <company>"). Upgrade that too.
            desc_l = desc.lower()
            if re.search(
                r"notice of intent[^.]*sole source|intent to (?:award|enter into) (?:a )?sole source",
                desc_l,
            ):
                opp["bidable"] = False
                opp["bidClass"] = "SOLE_INTENT"
                opp["bidBlockReason"] = (
                    "Sole-source intent confirmed in description — "
                    "contract is going to a named company")
            print(f"  ✓ {opp.get('title', '')[:55]}")
            print(f"      gate={gate} matched={matched!r} desc={len(desc)} chars bidable={opp.get('bidable', '?')}")
        except Exception as e:
            print(f"  ✗ {opp.get('title', '')[:55]} — {type(e).__name__}: {str(e)[:120]}")
    page.close()
    return opps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--min-score", type=int, default=40)
    ap.add_argument("--all", action="store_true",
                    help="Enrich EVERY non-dismissed lead (any score) instead of top-N.")
    args = ap.parse_args()

    data = json.loads(RESULTS_FILE.read_text())
    dismissed = load_dismissed()
    opps = [o for o in data["opportunities"]
            if o.get("noticeId") not in dismissed]
    if args.all:
        targets = opps
        print(f"Enriching ALL {len(targets)} non-dismissed leads (skipping {len(dismissed)} dismissed):")
    else:
        opps = [o for o in opps if o.get("relevanceScore", 0) >= args.min_score]
        opps.sort(key=lambda x: x["relevanceScore"], reverse=True)
        targets = opps[: args.top]
        print(f"Enriching top {len(targets)} hot leads (min score {args.min_score}, "
              f"{len(dismissed)} dismissed skipped):")
    if not targets:
        print("No leads to enrich.")
        return
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome", headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        try:
            enrich(targets, browser)
        finally:
            browser.close()

    data["enrichment"] = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "topN": len(targets),
        "mode": "all" if args.all else "topN",
        "note": "descriptionText/gateFound added for leads (SAM.gov rendered via Playwright)",
    }
    RESULTS_FILE.write_text(json.dumps(data, indent=2))
    if MC_FILE.exists():
        mc = json.loads(MC_FILE.read_text())
        by_id = {o.get("noticeId"): o for o in mc["opportunities"]}
        for t in targets:
            nid = t.get("noticeId")
            if nid in by_id:
                for k in ("descriptionText", "gateFound", "gateVerified",
                          "bidable", "bidClass", "bidBlockReason"):
                    if k in t:
                        by_id[nid][k] = t[k]
        mc["enrichment"] = data["enrichment"]
        MC_FILE.write_text(json.dumps(mc, indent=2))
        print(f"\nSynced enrichment to MC dashboard copy ({MC_FILE})")

    print("\n--- HOT LEAD SNIPPETS ---")
    for t in targets:
        gate = f"GATE: {t['gateFound']}" if t.get("gateVerified") else "gate: unknown"
        print(f"\n[{t['relevanceScore']}/100] {t['title']} | {gate}")
        print(f"  {t.get('descriptionText', '')[:400]}")


if __name__ == "__main__":
    main()
