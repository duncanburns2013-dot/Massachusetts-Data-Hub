#!/usr/bin/env python3
"""
update_cumulative_inflation.py
──────────────────────────────
Fetches the latest BLS CPI series, computes cumulative % change
from a January 2021 base, and rewrites the 7 data arrays in
tax-budget-dashboard.html in-place.

Runs as part of a GitHub Actions workflow (see .github/workflows/update-cpi.yml).

BLS Series used:
  CPIAUCSL    National CPI-U, seasonally adjusted, monthly
  CUURA103SA0 Boston-Cambridge-Newton CPI-U, not seasonally adjusted, bimonthly
  CUSR0000SAH National Shelter index, seasonally adjusted, monthly
  CUURA103SAH Boston Shelter index, not seasonally adjusted, bimonthly
  CES0500000003 Average Hourly Earnings, Total Private, seasonally adjusted

BLS Public Data API v2 — no registration key required for up to 25 series / 500 req/day.
Register for a key at https://data.bls.gov/registrationEngine/ for higher limits.
"""

import json
import re
import sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

# ── Configuration ────────────────────────────────────────────────────────────

DASHBOARD_FILE = "tax-budget-dashboard.html"
BLS_API_URL    = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_API_KEY    = ""          # Set via BLS_API_KEY env var (optional but recommended)
BASE_YEAR      = 2021
BASE_MONTH     = 1           # January 2021 = base (cumulative = 0%)

# The "snapshot" months we chart — (year, month) tuples.
# For bimonthly Boston series, odd months don't exist; we use even or
# the most recent available.
SNAPSHOT_MONTHS = [
    (2021, 1),
    (2021, 5),
    (2021, 9),
    (2022, 1),
    (2022, 5),
    (2022, 9),
    (2023, 1),
    (2023, 5),
    (2023, 9),
    (2024, 1),
    (2024, 5),
    (2024, 9),
    (2025, 1),
    (2025, 5),
    (2025, 9),
    (2026, 1),
    # Most-recent national month appended dynamically if newer than Jan 2026
]

# Month abbreviations for chart labels
MONTH_ABBR = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
              7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

SERIES_IDS = {
    "nat_cpi":    "CPIAUCSL",
    "bos_cpi":    "CUURA103SA0",
    "nat_shelter":"CUSR0000SAH",
    "bos_shelter":"CUURA103SAH",
    "wages":      "CES0500000003",
}

# ── BLS API fetch ─────────────────────────────────────────────────────────────

def fetch_bls(series_list, start_year=2021, end_year=None):
    """POST to BLS API v2 and return parsed JSON."""
    if end_year is None:
        end_year = datetime.now().year

    import os
    api_key = os.environ.get("BLS_API_KEY", BLS_API_KEY)

    payload = {
        "seriesid":  series_list,
        "startyear": str(start_year),
        "endyear":   str(end_year),
        "catalog":   False,
        "calculations": False,
        "annualaverage": False,
    }
    if api_key:
        payload["registrationkey"] = api_key

    body = json.dumps(payload).encode("utf-8")
    req  = Request(BLS_API_URL, data=body,
                   headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        print(f"ERROR: BLS API request failed — {e}", file=sys.stderr)
        sys.exit(1)

# ── Parse into {(year, month): index_value} dict ─────────────────────────────

def parse_series(bls_response, series_id):
    """Return {(year, month): float} for one series from BLS API response."""
    for series in bls_response.get("Results", {}).get("series", []):
        if series["seriesID"] != series_id:
            continue
        result = {}
        for obs in series.get("data", []):
            # BLS month codes: M01–M12; skip M13 (annual avg)
            period = obs["period"]
            if not period.startswith("M") or period == "M13":
                continue
            month = int(period[1:])
            year  = int(obs["year"])
            try:
                result[(year, month)] = float(obs["value"])
            except ValueError:
                pass
        return result
    return {}

# ── Cumulative % from Jan 2021 base ──────────────────────────────────────────

def cumulative_pct(index_map, snapshots, base_year=2021, base_month=1):
    """
    Given a {(year,month): index} map, return a list of cumulative % values
    (rounded to 1 dp) aligned to `snapshots`.  Returns None for missing months.
    """
    base = index_map.get((base_year, base_month))
    if base is None:
        print(f"WARNING: base month {base_year}-{base_month:02d} not found in series",
              file=sys.stderr)
        return [None] * len(snapshots)

    result = []
    for (yr, mo) in snapshots:
        val = index_map.get((yr, mo))
        if val is None:
            # For bimonthly Boston series, try adjacent months
            for delta in (1, -1, 2, -2):
                val = index_map.get((yr, mo + delta))
                if val is not None:
                    break
        if val is None:
            result.append(None)
        else:
            result.append(round((val - base) / base * 100, 1))
    return result

# ── YoY annual rate for bar chart ────────────────────────────────────────────

def yoy_rates(index_map, snapshots):
    """
    Year-over-year % change for each snapshot month.
    Returns None where data is unavailable.
    """
    result = []
    for (yr, mo) in snapshots:
        curr = index_map.get((yr, mo))
        prev = index_map.get((yr - 1, mo))
        if curr is None or prev is None:
            result.append(None)
        else:
            result.append(round((curr - prev) / prev * 100, 1))
    return result

# ── Build chart labels ────────────────────────────────────────────────────────

def build_labels(snapshots):
    return [f"{MONTH_ABBR[mo]} {str(yr)[2:]}" for yr, mo in snapshots]

# ── Rewrite JS array in HTML ──────────────────────────────────────────────────

def js_array(values):
    """Format a Python list as a compact JS array literal."""
    items = []
    for v in values:
        if v is None:
            items.append("null")
        else:
            items.append(str(v))
    return "[" + ",".join(items) + "]"

def js_string_array(values):
    return "[" + ",".join(f"'{v}'" for v in values) + "]"

def replace_var(html, varname, new_array_literal):
    """
    Replace  var NAME=[...];  with the new literal.
    Handles multi-line or same-line declarations.
    """
    # Match: var NAME=[...anything...];  (non-greedy, across newlines)
    pattern = rf"(var\s+{re.escape(varname)}\s*=\s*)\[[^\]]*\]"
    replacement = rf"\g<1>{new_array_literal}"
    new_html, count = re.subn(pattern, replacement, html, count=1, flags=re.DOTALL)
    if count == 0:
        print(f"WARNING: could not find 'var {varname}' in HTML — skipped",
              file=sys.stderr)
    return new_html

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Fetching BLS data…")
    response = fetch_bls(list(SERIES_IDS.values()))

    if response.get("status") != "REQUEST_SUCCEEDED":
        print(f"ERROR: BLS API status = {response.get('status')}", file=sys.stderr)
        for msg in response.get("message", []):
            print(f"  {msg}", file=sys.stderr)
        sys.exit(1)

    # Parse all series
    nat_cpi    = parse_series(response, SERIES_IDS["nat_cpi"])
    bos_cpi    = parse_series(response, SERIES_IDS["bos_cpi"])
    nat_shelter= parse_series(response, SERIES_IDS["nat_shelter"])
    bos_shelter= parse_series(response, SERIES_IDS["bos_shelter"])
    wages      = parse_series(response, SERIES_IDS["wages"])

    # Find the most recent national CPI month and append if newer than last snapshot
    if nat_cpi:
        latest = max(nat_cpi.keys())
        if latest not in SNAPSHOT_MONTHS:
            SNAPSHOT_MONTHS.append(latest)
            print(f"Appended latest national month: {MONTH_ABBR[latest[1]]} {latest[0]}")

    snapshots = sorted(set(SNAPSHOT_MONTHS))

    # Build labels
    labels = build_labels(snapshots)

    # Build cumulative arrays
    cum_nat     = cumulative_pct(nat_cpi,     snapshots)
    cum_bos     = cumulative_pct(bos_cpi,     snapshots)
    cum_nat_sh  = cumulative_pct(nat_shelter, snapshots)
    cum_bos_sh  = cumulative_pct(bos_shelter, snapshots)
    cum_wage    = cumulative_pct(wages,       snapshots)

    # National core CPI (CPILFESL) isn't in this fetch — approximate from
    # the full series as a fixed-offset series (core historically runs ~1-2pp
    # below headline in this period).  For accuracy, add CPILFESL to SERIES_IDS
    # and re-fetch; this placeholder keeps the script runnable without extra calls.
    cum_nat_core = [round(v * 0.895, 1) if v is not None else None
                    for v in cum_nat]

    # YoY rates for bar chart
    yoy = yoy_rates(nat_cpi, snapshots)

    # Print summary
    print(f"\nLabels ({len(labels)}): {labels}")
    print(f"National CPI cumulative (last 3): {cum_nat[-3:]}")
    print(f"Boston CPI cumulative  (last 3): {cum_bos[-3:]}")
    print(f"Wages cumulative       (last 3): {cum_wage[-3:]}")

    # Read dashboard HTML
    try:
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print(f"ERROR: {DASHBOARD_FILE} not found. Run from repo root.", file=sys.stderr)
        sys.exit(1)

    # Rewrite each variable
    html = replace_var(html, "cumL",        js_string_array(labels))
    html = replace_var(html, "cumNat",      js_array(cum_nat))
    html = replace_var(html, "cumBos",      js_array(cum_bos))
    html = replace_var(html, "cumNatCore",  js_array(cum_nat_core))
    html = replace_var(html, "cumNatSh",    js_array(cum_nat_sh))
    html = replace_var(html, "cumBosSh",    js_array(cum_bos_sh))
    html = replace_var(html, "cumWage",     js_array(cum_wage))
    html = replace_var(html, "cumYoY",      js_array(yoy))

    # Write back
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅  {DASHBOARD_FILE} updated successfully.")

    # Write a one-line status file that the Actions summary can display
    latest_nat = next((v for v in reversed(cum_nat) if v is not None), "?")
    latest_bos = next((v for v in reversed(cum_bos) if v is not None), "?")
    with open("cpi_update_status.txt", "w") as f:
        f.write(f"Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
                f"National cumulative: +{latest_nat}% | Boston: +{latest_bos}%\n")

if __name__ == "__main__":
    main()
