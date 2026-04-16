#!/usr/bin/env python3
"""
update-cbp-encounters.py
Downloads CBP encounter CSVs and updates immigration-dashboard.html.

CBP doesn't have a stable REST API, but publishes CSV files at their
Public Data Portal (cbp.gov/newsroom/stats/cbp-public-data-portal).

Strategy:
  1. Try known CSV URL patterns for current FY
  2. Try OHSS (DHS Office of Homeland Security Statistics) mirror
  3. Fall back to a local CSV the user can drop at data/cbp-encounters-latest.csv

No API key needed.

Updates:
  - Encounter bar chart data  â  immigration-dashboard.html
  - FY callout text           â  immigration-dashboard.html
  - data/cbp-encounters-latest.json
"""
import csv, io, json, os, re, sys
from urllib.request import urlopen, Request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMMIGRATION_HTML = os.path.join(BASE_DIR, "immigration-dashboard.html")
LOCAL_CSV = os.path.join(BASE_DIR, "data", "cbp-encounters-latest.csv")

# Current chart data from immigration-dashboard.html
CHART_LABELS = ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26*"]
BASELINE = {
    "FY17": 415517, "FY18": 521090, "FY19": 977509, "FY20": 458088,
    "FY21": 1734686, "FY22": 2378944, "FY23": 3201144, "FY24": 2900000,
    "FY25": 237538, "FY26*": 60940,
}

# URLs to try (CBP shifts these with each monthly release)
CANDIDATE_URLS = [
    # FY2026 data pages
    "https://www.cbp.gov/sites/default/files/assets/documents/nationwide-encounters-fy26-td.csv",
    "https://www.cbp.gov/sites/default/files/assets/documents/2026-Apr/nationwide-encounters.csv",
    "https://www.cbp.gov/sites/default/files/assets/documents/2026-Mar/nationwide-encounters.csv",
    # FY2025 final
    "https://www.cbp.gov/sites/default/files/assets/documents/2025-Dec/nationwide-encounters-fy2025-data.csv",
    "https://www.cbp.gov/sites/default/files/assets/documents/2025-Nov/nationwide-encounters.csv",
    # OHSS mirror
    "https://ohss.dhs.gov/sites/default/files/2026-04/cbp_encounters.csv",
    "https://ohss.dhs.gov/sites/default/files/2026-03/cbp_encounters.csv",
]


def fetch_csv_url(url):
    """Download CSV, return list of dicts or None."""
    req = Request(url, headers={"User-Agent": "MA-Data-Hub/1.0"})
    try:
        with urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8-sig")
        if not text.strip() or "<html" in text[:200].lower():
            return None  # Got an error page, not CSV
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        return rows if rows else None
    except Exception:
        return None


def parse_fy_totals(rows):
    """
    Parse rows into {FY_label: total_encounters}.
    CBP CSV formats vary, so we try multiple column-name patterns.
    """
    fy_col = None
    count_cols = []

    # Discover columns
    headers = list(rows[0].keys()) if rows else []
    for h in headers:
        hl = h.lower().strip()
        if "fiscal" in hl and "year" in hl:
            fy_col = h
        elif hl in ("encounter count", "encounters", "encounter_count", "total"):
            count_cols.append(h)
    # If no specific count col found, look for any numeric-ish column
    if not count_cols:
        for h in headers:
            hl = h.lower().strip()
            if any(k in hl for k in ("count", "apprehension", "inadmissible")):
                count_cols.append(h)

    if not fy_col:
        print("  WARN: No 'Fiscal Year' column found. Headers:", headers[:10])
        return None

    totals = {}
    for row in rows:
        fy_raw = row.get(fy_col, "").strip()
        if not fy_raw:
            continue
        # Normalize to "FYXX" format
        try:
            fy_num = int(fy_raw)
            fy_label = f"FY{str(fy_num)[-2:]}"
        except ValueError:
            fy_label = fy_raw

        count = 0
        for cc in count_cols:
            try:
                count += int(row[cc].strip().replace(",", ""))
            except (ValueError, AttributeError, KeyError):
                pass
        if count > 0:
            totals[fy_label] = totals.get(fy_label, 0) + count

    return totals if totals else None


def try_auto_fetch():
    """Try candidate URLs one by one."""
    for url in CANDIDATE_URLS:
        print(f"  Trying {url.split('/')[-1]}...")
        rows = fetch_csv_url(url)
        if rows:
            totals = parse_fy_totals(rows)
            if totals:
                print(f"  â Got data from: {url}")
                return totals
    return None


def update_dashboard(fy_data):
    """Merge new data into immigration-dashboard.html."""
    if not os.path.exists(IMMIGRATION_HTML):
        print(f"  SKIP: {IMMIGRATION_HTML} not found.")
        return

    with open(IMMIGRATION_HTML, "r", encoding="utf-8") as f:
        html = f.read()
    orig = html

    updated = dict(BASELINE)
    for fy, val in fy_data.items():
        if fy in updated and val != updated[fy]:
            print(f"  {fy}: {updated[fy]:,} â {val:,}")
            updated[fy] = val

    old_vals = [BASELINE[l] for l in CHART_LABELS]
    new_vals = [updated[l] for l in CHART_LABELS]

    old_arr = ",".join(str(x) for x in old_vals)
    new_arr = ",".join(str(x) for x in new_vals)

    if old_arr != new_arr and old_arr in html:
        html = html.replace(f"data:[{old_arr}]", f"data:[{new_arr}]", 1)
        print("  Chart data array updated.")

    # Update callout numbers
    for label, key, formatted in [
        ("FY25", "FY25", f"{updated['FY25']:,}"),
        ("FY26", "FY26*", f"{updated['FY26*']:,}"),
    ]:
        old_formatted = f"{BASELINE[key]:,}"
        if old_formatted != formatted:
            n = html.count(old_formatted)
            if n > 0:
                html = html.replace(old_formatted, formatted)
                print(f"  {label} callout: {old_formatted} â {formatted} ({n}x)")

    if html != orig:
        with open(IMMIGRATION_HTML, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  â {IMMIGRATION_HTML} updated.")
    else:
        print("  No dashboard changes needed.")


def main():
    print("=== CBP Encounter Data Update ===\n")

    # Try auto-fetch first
    print("Attempting auto-fetch from CBP / OHSS...")
    fy_data = try_auto_fetch()

    # Fall back to local CSV
    if not fy_data and os.path.exists(LOCAL_CSV):
        print(f"\n  Auto-fetch failed. Trying local CSV: {LOCAL_CSV}")
        with open(LOCAL_CSV, "r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        fy_data = parse_fy_totals(rows)

    if fy_data:
        print(f"\nEncounter data ({len(fy_data)} fiscal years):")
        for fy in sorted(fy_data.keys()):
            marker = " â" if BASELINE.get(fy) and fy_data[fy] != BASELINE.get(fy) else ""
            print(f"  {fy}: {fy_data[fy]:,}{marker}")
        update_dashboard(fy_data)
    else:
        print("\nâ ï¸  Could not fetch CBP data automatically.")
        print("    CBP changes their CSV download URLs each month.")
        print("    To update manually:")
        print("    1. Go to https://www.cbp.gov/newsroom/stats/cbp-public-data-portal")
        print("    2. Download the latest Nationwide Encounters CSV")
        print(f"    3. Save it to: data/cbp-encounters-latest.csv")
        print("    4. Re-run this script")

    # Save JSON regardless
    out = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "source": "CBP Public Data Portal",
        "auto_fetched": fy_data is not None,
        "fy_totals": fy_data or BASELINE,
        "baseline": BASELINE,
    }
    json_path = os.path.join(BASE_DIR, "data", "cbp-encounters-latest.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nData â {json_path}")
    print("â¨ CBP update complete.\n")


if __name__ == "__main__":
    main()
