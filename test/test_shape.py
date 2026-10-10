#!/usr/bin/env python3
"""Live output-shape test for sec-xbrl-financials-csv.

Runs against the REAL SEC EDGAR API (no mocks) and verifies the tidy CSV shape.
Also the basis of ./health-check. Plain stdlib; no pytest required.

    python3 test/test_shape.py          # full: resolve AAPL ticker + several metrics
    python3 test/test_shape.py --quick  # fast: CIK 320193 direct, one metric

Exit 0 = healthy, 1 = failure or output-shape change.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import sec_xbrl as sx  # noqa: E402

QUICK = "--quick" in sys.argv
APPLE_CIK = 320193


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    try:
        if QUICK:
            rows = sx.company_rows("320193", concepts=["Assets"])
            identifier = "CIK 320193"
        else:
            rows = sx.company_rows(
                "AAPL",
                concepts=["Assets", "NetIncomeLoss", "Revenues",
                          "RevenueFromContractWithCustomerExcludingAssessedTax"],
            )
            identifier = "AAPL"
    except sx.SecError as e:
        fail(f"live SEC fetch failed for {('CIK 320193' if QUICK else 'AAPL')}: {e}")

    # 1. non-empty
    if not rows:
        fail(f"{identifier}: zero rows returned")

    # 2. every row has exactly the documented columns
    expected = set(sx.COLUMNS)
    for r in rows[:50]:
        if set(r.keys()) != expected:
            fail(f"row keys {sorted(r.keys())} != schema {sorted(expected)}")

    # 3. CSV header is exactly the documented schema (shape-change tripwire)
    buf = io.StringIO()
    sx.write_csv(rows, buf)
    header = buf.getvalue().splitlines()[0]
    if header != ",".join(sx.COLUMNS):
        fail(f"CSV header drifted: {header!r}")

    # 4. an 'Assets' datapoint exists with a numeric value and sane period_end
    assets = [r for r in rows if r["concept"] == "Assets"]
    if not assets:
        fail(f"{identifier}: expected 'Assets' concept not present")
    a = assets[0]
    try:
        float(a["value"])
    except (TypeError, ValueError):
        fail(f"'Assets' value not numeric: {a['value']!r}")
    if not str(a["period_end"]).startswith(("19", "20")):
        fail(f"'Assets' period_end looks wrong: {a['period_end']!r}")

    # 5. dedupe invariant: one row per period (concept,unit,start,end)
    seen = set()
    for r in rows:
        k = (r["taxonomy"], r["concept"], r["unit"],
             r["period_start"], r["period_end"])
        if k in seen:
            fail(f"duplicate period after dedupe: {k}")
        seen.add(k)

    print(f"PASS: {identifier} -> {len(rows)} rows, schema OK, "
          f"{len(assets)} Assets points, dedupe clean.")
    sys.exit(0)


if __name__ == "__main__":
    main()
