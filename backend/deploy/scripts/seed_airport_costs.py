"""Seed script: Add realistic cost data to Caribbean Loop airports.

Run from project root with .venv activated:
  cd /home/shawn/projects/pararig-ops/backend
  source .venv/bin/activate
  python3 deploy/scripts/seed_airport_costs.py
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = "/home/shawn/projects/pararig-ops/backend/pararig_ops.db"

# ── Cost data per airport ─────────────────────────────────────────────
# Format: (icao, landing, parking, handling, customs, overflight_permit, payment_type, landing_notes)

AIRPORT_COSTS = [
    # MYNN — Lynden Pindling International, Nassau, Bahamas
    ("MYNN", 150.0, 30.0, 75.0, 50.0, 200.0, "mixed",
     "Cash or credit; permit 24hr advance for non-sched"),

    # KMIA — Miami International, Florida, USA
    ("KMIA", 450.0, 85.0, 200.0, 100.0, 0.0, "credit",
     "Credit card only; ramp fees variable by FBO"),

    # MMUN — Cancún International, Quintana Roo, Mexico
    ("MMUN", 200.0, 40.0, 100.0, 75.0, 150.0, "mixed",
     "Mexico overflight permit required; cash/credit accepted"),

    # MTPP — Toussaint Louverture International, Port-au-Prince, Haiti
    ("MTPP", 350.0, 50.0, 150.0, 100.0, 250.0, "cash_only",
     "CASH ONLY — USD preferred; permit must be arranged through handling agent"),

    # MUHA — José Martí International, Havana, Cuba
    ("MUHA", 300.0, 45.0, 120.0, 80.0, 300.0, "cash_only",
     "CASH ONLY — EUR/USD accepted; Cuba landing permit required 72hr advance"),

    # MDPC — Punta Cana International, La Altagracia, Dominican Republic
    ("MDPC", 180.0, 35.0, 90.0, 60.0, 175.0, "mixed",
     "Tourist card fee $10/pax may apply; cash or card accepted"),
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check airports table exists
    tables = [row[0] for row in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]

    if "airports" not in tables:
        print("❌ airports table not found — run migrations first")
        conn.close()
        return

    # Check for new columns
    cols = [row[1] for row in cur.execute("PRAGMA table_info(airports)").fetchall()]
    required_cols = [
        "landing_fee_usd", "overnight_parking_usd", "handling_fee_usd",
        "customs_fee_usd", "overflight_permit_cost_usd", "payment_type",
        "landing_notes",
    ]
    missing = [c for c in required_cols if c not in cols]
    if missing:
        print(f"❌ Missing columns: {missing} — run migration first")
        conn.close()
        return

    updated = 0
    skipped = 0
    not_found = 0

    for row in AIRPORT_COSTS:
        (
            icao, landing, parking, handling, customs,
            overflight, payment_type, notes,
        ) = row

        # Check airport exists
        cur.execute("SELECT COUNT(*) FROM airports WHERE icao_code = ?", (icao,))
        if cur.fetchone()[0] == 0:
            print(f"  ⚠️  {icao} not found in airports table — skipping")
            not_found += 1
            continue

        cur.execute(
            """UPDATE airports SET
                landing_fee_usd = ?,
                overnight_parking_usd = ?,
                handling_fee_usd = ?,
                customs_fee_usd = ?,
                overflight_permit_cost_usd = ?,
                payment_type = ?,
                landing_notes = ?,
                last_verified = ?
            WHERE icao_code = ?""",
            (
                landing, parking, handling, customs,
                overflight, payment_type, notes,
                datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                icao,
            ),
        )
        if cur.rowcount > 0:
            print(f"  ✅ {icao}: landing=${landing} parking=${parking} handling=${handling} customs=${customs} ({payment_type})")
            updated += 1
        else:
            skipped += 1

    conn.commit()
    conn.close()

    print(f"\n{'='*50}")
    print(f"  Caribbean Loop cost seed complete:")
    print(f"  ✅ {updated} airports updated")
    if not_found:
        print(f"  ⚠️  {not_found} ICAOs not in database")
    print(f"{'='*50}")


if __name__ == "__main__":
    seed()
