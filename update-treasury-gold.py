#!/usr/bin/env python3
"""
update-treasury-gold.py
Fetches U.S. Treasury gold reserve data from the Fiscal Data API.

Endpoint: api.fiscaldata.treasury.gov  â  /v1/accounting/od/gold_reserve
No API key needed â completely free and open.

Updates:
  - MASTER_DATA.md gold holdings table
  - data/treasury-gold-latest.json (for dashboard consumption)

Does NOT touch any dashboard HTML. The docstring used to claim it updated
"tax-budget-dashboard.html (gold reserve info box, if present)" and the module
defined a TAX_BUDGET_HTML path to match, but nothing ever read that constant and
no such info box exists -- the dashboard makes no mention of gold at all. The
claim and the unused path have been removed rather than left to imply a coupling
that was never there.
"""
import json, os, re, sys
from urllib.request import urlopen, Request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_DATA = os.path.join(BASE_DIR, "MASTER_DATA.md")

API_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
    "v1/accounting/od/gold_reserve"
    "?sort=-record_date"
    "&page[size]=10"
    "&fields=record_date,facility_desc,fine_troy_ounce_qty,book_value_amt"
)

# Current values in MASTER_DATA.md (for comparison)
CURRENT = {"total": 261.5, "fort_knox": 147.3, "west_point": 54.1, "denver": 43.9}

# Facility name mapping (API names â short names)
FACILITY_MAP = {
    "Fort Knox, KY - Deep Storage": "fort_knox",
    "West Point, NY - Deep Storage": "west_point",
    "Denver, CO - Deep Storage": "denver",
}


def fetch_gold():
    req = Request(API_URL, headers={"User-Agent": "MA-Data-Hub/1.0"})
    try:
        with urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        return data.get("data", [])
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def main():
    print("=== Treasury Gold Reserve Update ===\n")

    records = fetch_gold()
    if not records:
        print("ERROR: Could not fetch gold data from Treasury API.")
        sys.exit(1)

    latest_date = records[0]["record_date"]
    latest = [r for r in records if r["record_date"] == latest_date]

    print(f"Report date: {latest_date}")
    print(f"Facilities:  {len(latest)}\n")

    total_oz = 0
    total_bv = 0
    facilities = {}
    new_vals = {}

    for r in latest:
        name = r["facility_desc"]
        oz = float(r["fine_troy_ounce_qty"])
        bv = float(r["book_value_amt"])
        facilities[name] = {"troy_ounces": oz, "book_value": bv}
        total_oz += oz
        total_bv += bv
        short = FACILITY_MAP.get(name)
        if short:
            new_vals[short] = round(oz / 1e6, 1)
        print(f"  {name}: {oz:,.0f} oz (${bv:,.0f})")

    new_vals["total"] = round(total_oz / 1e6, 1)
    print(f"\n  TOTAL: {total_oz:,.0f} oz ({new_vals['total']}M)")

    # ââ Compare to baseline ââ
    changed = False
    for key in CURRENT:
        old = CURRENT[key]
        new = new_vals.get(key, old)
        if old != new:
            print(f"\n  â ï¸  CHANGE: {key} {old}M â {new}M")
            changed = True
    if not changed:
        print("\n  â Holdings unchanged from current MASTER_DATA values.")

    # ââ Update MASTER_DATA.md ââ
    if os.path.exists(MASTER_DATA):
        with open(MASTER_DATA, "r", encoding="utf-8") as f:
            md = f.read()
        orig = md

        pairs = [
            ("Total holdings", "total"), ("Fort Knox", "fort_knox"),
            ("West Point", "west_point"), ("Denver", "denver"),
        ]
        today = datetime.now().strftime("%b %Y")
        for label, key in pairs:
            old_val = CURRENT[key]
            new_val = new_vals.get(key, old_val)
            unit = "fine troy oz" if label == "Total holdings" else "oz"
            old_str = f"| {label} | {old_val}M {unit}"
            new_str = f"| {label} | {new_val}M {unit}"
            if old_str in md and old_val != new_val:
                md = md.replace(old_str, new_str)
                print(f"  MASTER_DATA: {label} {old_val}M â {new_val}M")

        # Update verification dates
        for line_match in ["Treasury.gov"]:
            pattern = re.compile(r"(Treasury\.gov \| â )\w+ \d{4}")
            md = pattern.sub(rf"\g<1>{today}", md)

        if md != orig:
            with open(MASTER_DATA, "w", encoding="utf-8") as f:
                f.write(md)
            print("  â MASTER_DATA.md updated.")
        else:
            print("  MASTER_DATA.md â no changes needed.")

    # ââ Save JSON ââ
    out = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "source": "U.S. Treasury Fiscal Data API",
        "api_url": API_URL,
        "record_date": latest_date,
        "total_troy_ounces": total_oz,
        "total_millions": new_vals["total"],
        "book_value_per_oz": 42.2222,
        "total_book_value": total_bv,
        "facilities": facilities,
        "summary_millions": new_vals,
    }
    json_path = os.path.join(BASE_DIR, "data", "treasury-gold-latest.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nRaw data â {json_path}")
    print("â¨ Treasury gold update complete.\n")


if __name__ == "__main__":
    main()
