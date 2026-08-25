#!/usr/bin/env python3
"""HigherGov intel pass — estimated value, deadlines, and shaping signals.

SAM.gov hides value/prior-award data; HigherGov aggregates it per opportunity
(estimated value from historical NSN pricing, "signs of shaping", buyer, exact
deadline). This script searches HigherGov for each hot lead (by solicitation
number), opens the matching detail page, and merges the intel into results.json
+ the MC dashboard copy.

Usage:
    .venv/bin/python enrich_highergov.py --top 5
    .venv/bin/python enrich_highergov.py --notice-id 2969899ef99f40b5bf672ab2d00bf41c
    .venv/bin/python enrich_highergov.py --url https://www.highergov.com/contract-opportunity/...

Search box note: HigherGov's ?q= URL param is a JS shell; you must type into
the "Search by Name or ID" input and press Enter (verified Aug 10, 2026).
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

OUTPUT_DIR = Path(__file__).resolve().parent
RESULTS_FILE = OUTPUT_DIR / "results.json"
MC_FILE = Path.home() / "ai-infra/MissionControl/sdvosb/results.json"

SEARCH_URL = "https://www.highergov.com/contract-opportunity/"


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def extract_intel(text: str) -> dict:
    """Pull decision fields from a HigherGov detail page body text.

    HigherGov renders label/value pairs newline-separated ("Est. Value Range
    \\n$23,250 ..."), not pipe-separated. Also pulls the DLA standard unit
    price and the most recent purchase rows (awardee-level intel).
    """
    def grab(label, maxlen=200):
        m = re.search(re.escape(label) + r"\s*\n([^\n]+)", text)
        return _clean(m.group(1))[:maxlen] if m else ""

    intel = {
        "deadline": grab("Deadline"),
        "posted": grab("Posted"),
        "setAside": grab("Set Aside"),
        "naics": grab("NAICS"),
        "valueRange": grab("Est. Value Range"),
        "valueNote": grab("value based on historical"),
        "shaping": grab("Signs of Shaping"),
        "unitPrice": grab("Standard Unit Price (DLA)"),
        "competition": grab("Est. Level of Competition"),
        "buyer": grab("Buyer"),
    }
    # Most recent purchases table — capture the raw rows (contract, awardee,
    # set-aside, unit price) up to a reasonable window.
    m = re.search(r"Most Recent (?:DLA )?Purchases\s*\n(.{0,600}?)(?:\n\s*\n|\n[A-Z][A-Za-z ]{6,}\n|$)", text, re.S)
    intel["recentPurchases"] = _clean(m.group(1))[:500] if m else ""
    return intel


def search_highergov(page, query: str) -> str:
    """Search HigherGov, return detail-page URL of the result row matching query.

    The results table mixes many opportunities — the first row is NOT the
    match. Only return a link when the row text contains a meaningful token
    of the query (solicitation number or >= 4-char title word).
    """
    tokens = [t for t in re.split(r"[^a-z0-9]+", query.lower()) if len(t) >= 4]
    if not tokens:
        return ""
    page.goto(SEARCH_URL, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    box = page.query_selector("input[placeholder*='Search by Name or ID']")
    if not box:
        box = page.query_selector("input[type=search]")
    if not box:
        return ""
    box.fill(query)
    box.press("Enter")
    page.wait_for_timeout(8000)
    rows = page.query_selector_all("table tbody tr")
    for row in rows:
        row_text = (row.inner_text() or "").lower()
        if any(tok in row_text for tok in tokens):
            link = row.query_selector("a[href*='/contract-opportunity/']")
            if link:
                href = link.get_attribute("href")
                if href:
                    return href if href.startswith("http") else "https://www.highergov.com" + href
    return ""


def enrich_one(page, opp: dict) -> dict:
    """Enrich a single opportunity dict with HigherGov intel (best-effort)."""
    opp.setdefault("highergov", {})
    hg = opp["highergov"]
    hg["status"] = "not found"

    q = (opp.get("solicitationNumber") or opp.get("title") or "").strip()
    if not q:
        return opp
    try:
        url = search_highergov(page, q)
        if not url:
            return opp
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(6000)
        body = page.inner_text("body")
        intel = extract_intel(body)
        if intel.get("deadline") or intel.get("valueRange"):
            hg.update({"status": "found", "url": url, **intel})
        else:
            hg["status"] = "found-no-data"
            hg["url"] = url
    except Exception as e:
        hg["status"] = "error"
        hg["error"] = f"{type(e).__name__}: {str(e)[:100]}"
    return opp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--notice-id", default=None)
    ap.add_argument("--url", default=None, help="skip search; enrich this HigherGov URL directly")
    args = ap.parse_args()

    data = json.loads(RESULTS_FILE.read_text())
    if args.url:
        # Direct-URL mode: match the record the URL belongs to. HigherGov
        # slugs embed the solicitation number ("17-sling-...-spe8ef26t1608-...").
        # The trailing "-k-<hash>" is a random suffix — take the last token of
        # >= 6 alnum chars as the solicitation key.
        tokens = re.findall(r"[a-z0-9]{6,}", args.url.lower())
        sol_key = tokens[-1] if tokens else ""
        targets = []
        for o in data["opportunities"]:
            sol = (o.get("solicitationNumber") or "").lower()
            if sol and (sol_key in sol or sol in args.url.lower()):
                targets.append(o)
        if not targets:
            # Fallback: match by slug words against titles (e.g. "sling")
            words = [w for w in re.findall(r"[a-z]+", args.url.lower()) if len(w) > 3]
            targets = [o for o in data["opportunities"]
                       if any(w in (o.get("title") or "").lower() for w in words)][:1]
        if not targets:
            print("No matching record for URL — nothing to attach intel to.")
            return
    elif args.notice_id:
        targets = [o for o in data["opportunities"] if o.get("noticeId") == args.notice_id]
    else:
        opps = sorted(data["opportunities"], key=lambda x: x.get("relevanceScore", 0), reverse=True)
        targets = opps[: args.top]
    if not targets:
        print("No targets.")
        return

    print(f"HigherGov intel for {len(targets)} lead(s):")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome", headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(
            user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/151.0 Safari/537.36")
        )
        try:
            for opp in targets:
                if args.url:
                    opp["highergov"] = {"status": "found", "url": args.url}
                    try:
                        page.goto(args.url, timeout=45000, wait_until="domcontentloaded")
                        page.wait_for_timeout(6000)
                        opp["highergov"].update(extract_intel(page.inner_text("body")))
                    except Exception as e:
                        opp["highergov"]["status"] = "error"
                        opp["highergov"]["error"] = str(e)[:100]
                else:
                    enrich_one(page, opp)
                hg = opp.get("highergov", {})
                print(f"  {opp.get('title', '')[:50]:<52} {hg.get('status','?'):<16} {hg.get('valueRange','')}")
        finally:
            browser.close()

    data["highergov"] = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "note": "estimated value/deadline/shaping from HigherGov (best-effort per lead)",
    }
    RESULTS_FILE.write_text(json.dumps(data, indent=2))
    if MC_FILE.exists():
        mc = json.loads(MC_FILE.read_text())
        by_id = {o.get("noticeId"): o for o in mc["opportunities"]}
        for t in targets:
            nid = t.get("noticeId")
            if nid in by_id and t.get("highergov"):
                by_id[nid]["highergov"] = t["highergov"]
        mc["highergov"] = data["highergov"]
        MC_FILE.write_text(json.dumps(mc, indent=2))
        print(f"\nSynced HigherGov intel to MC dashboard copy ({MC_FILE})")


if __name__ == "__main__":
    main()
