#!/usr/bin/env python3
"""
update_cumulative_inflation.py  (v4)

National CPI + wages + shelter  →  BLS API  (working, key optional)
Boston CPI + shelter            →  FRED API (free key from fred.stlouisfed.org)

Repo secrets needed:
  BLS_API_KEY   (optional but recommended — bls.gov/registrationEngine)
  FRED_API_KEY  (required for Boston — fred.stlouisfed.org/docs/api/api_key.html)
"""

import json
import os
import re
import sys
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import urlencode

DASHBOARD_FILE = "tax-budget-dashboard.html"
BASE_YEAR  = 2021
BASE_MONTH = 1

SNAPSHOT_MONTHS = [
    (2021, 1), (2021, 5), (2021, 9),
    (2022, 1), (2022, 5), (2022, 9),
    (2023, 1), (2023, 5), (2023, 9),
    (2024, 1), (2024, 5), (2024, 9),
    (2025, 1), (2025, 5), (2025, 9),
    (2026, 1),
]

MONTH_ABBR = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
              7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

# BLS series (national — work without key, better with key)
BLS_SERIES = {
    "nat_cpi":    "CUSR0000SA0",
    "nat_shelter":"CUSR0000SAH",
    "wages":      "CES0500000003",
}

# FRED series (Boston local — requires free FRED API key)
FRED_SERIES = {
    "bos_cpi":    "CUURA103SA0",
    "bos_shelter":"CUURA103SAH",
}

# ── BLS fetch ────────────────────────────────────────────────────────────────

def fetch_bls(series_list, start_year=2020, end_year=None):
    if end_year is None:
        end_year = datetime.now().year
    api_key = os.environ.get("BLS_API_KEY", "")
    payload = {
        "seriesid": series_list,
        "startyear": str(start_year),
        "endyear": str(end_year),
        "catalog": False,
        "calculations": False,
        "annualaverage": False,
    }
    if api_key:
        payload["registrationkey"] = api_key
    body = json.dumps(payload).encode("utf-8")
    req = Request("https://api.bls.gov/publicAPI/v2/timeseries/data/",
                  data=body, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode())
            print(f"BLS status: {result.get('status')}")
            for msg in result.get("message", []):
                print(f"  BLS: {msg}")
            return result
    except URLError as e:
        print(f"ERROR: BLS request failed — {e}", file=sys.stderr)
        return None

def parse_bls_series(response, series_id):
    if not response:
        return {}
    for s in response.get("Results", {}).get("series", []):
        if s["seriesID"] != series_id:
            continue
        result = {}
        for obs in s.get("data", []):
            p = obs["period"]
            if not p.startswith("M") or p == "M13":
                continue
            try:
                result[(int(obs["year"]), int(p[1:]))] = float(obs["value"])
            except ValueError:
                pass
        if result:
            keys = sorted(result.keys())
            print(f"  {series_id}: {len(result)} obs, "
                  f"{keys[0][0]}-{keys[0][1]:02d} to {keys[-1][0]}-{keys[-1][1]:02d}, "
                  f"base={result.get((BASE_YEAR, BASE_MONTH))}")
        else:
            print(f"  {series_id}: no data returned")
        return result
    print(f"  {series_id}: not found in BLS response")
    return {}

# ── FRED fetch ───────────────────────────────────────────────────────────────

def fetch_fred_series(series_id, fred_key, start="2020-01-01"):
    params = urlencode({
        "series_id": series_id,
        "api_key": fred_key,
        "file_type": "json",
        "observation_start": start,
        "frequency": "m",          # monthly — FRED aggregates bimonthly to monthly
    })
    url = f"https://api.stlouisfed.org/fred/series/observations?{params}"
    try:
        with urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode())
        result = {}
        for obs in data.get("observations", []):
            if obs["value"] == ".":   # FRED uses "." for missing
                continue
            try:
                date = obs["date"]    # "YYYY-MM-DD"
                yr, mo = int(date[:4]), int(date[5:7])
                result[(yr, mo)] = float(obs["value"])
            except (ValueError, IndexError):
                pass
        if result:
            keys = sorted(result.keys())
            print(f"  {series_id} (FRED): {len(result)} obs, "
                  f"{keys[0][0]}-{keys[0][1]:02d} to {keys[-1][0]}-{keys[-1][1]:02d}, "
                  f"base={result.get((BASE_YEAR, BASE_MONTH))}")
        else:
            print(f"  {series_id} (FRED): no data")
        return result
    except URLError as e:
        print(f"  {series_id} (FRED): request failed — {e}")
        return {}

# ── Calculations ─────────────────────────────────────────────────────────────

def cumulative_pct(index_map, snapshots):
    base = index_map.get((BASE_YEAR, BASE_MONTH))
    if base is None:
        return [None] * len(snapshots)
    result = []
    for (yr, mo) in snapshots:
        val = index_map.get((yr, mo))
        if val is None:
            for delta in (1, -1, 2, -2):
                adj = mo + delta
                if 1 <= adj <= 12:
                    val = index_map.get((yr, adj))
                    if val is not None:
                        break
        result.append(round((val - base) / base * 100, 1) if val is not None else None)
    return result

def yoy_rates(index_map, snapshots):
    result = []
    for (yr, mo) in snapshots:
        curr = index_map.get((yr, mo))
        prev = index_map.get((yr - 1, mo))
        result.append(round((curr - prev) / prev * 100, 1)
                      if curr is not None and prev is not None else None)
    return result

def build_labels(snapshots):
    return [f"{MONTH_ABBR[mo]} {str(yr)[2:]}" for yr, mo in snapshots]

# ── HTML rewriting ────────────────────────────────────────────────────────────

def js_array(values):
    return "[" + ",".join("null" if v is None else str(v) for v in values) + "]"

def js_string_array(values):
    return "[" + ",".join(f"'{v}'" for v in values) + "]"

def replace_var(html, varname, new_literal):
    pattern = rf"(var\s+{re.escape(varname)}\s*=\s*)\[[^\]]*\]"
    new_html, count = re.subn(pattern, rf"\g<1>{new_literal}", html, count=1, flags=re.DOTALL)
    if count == 0:
        print(f"  WARNING: 'var {varname}' not found in HTML")
    return new_html

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    fred_key = os.environ.get("FRED_API_KEY", "")
    if not fred_key:
        print("WARNING: FRED_API_KEY not set — Boston series will be null.\n"
              "Get a free key at fred.stlouisfed.org/docs/api/api_key.html\n"
              "and add it as a repo secret named FRED_API_KEY.")

    # ── Fetch BLS (national) ──
    print("Fetching BLS data (national)...")
    bls_response = fetch_bls(list(BLS_SERIES.values()))

    print("\nParsing BLS series:")
    nat_cpi     = parse_bls_series(bls_response, BLS_SERIES["nat_cpi"])
    nat_shelter = parse_bls_series(bls_response, BLS_SERIES["nat_shelter"])
    wages       = parse_bls_series(bls_response, BLS_SERIES["wages"])

    # ── Fetch FRED (Boston) ──
    bos_cpi = bos_shelter = {}
    if fred_key:
        print("\nFetching FRED data (Boston)...")
        bos_cpi     = fetch_fred_series(FRED_SERIES["bos_cpi"],     fred_key)
        bos_shelter = fetch_fred_series(FRED_SERIES["bos_shelter"],  fred_key)
    else:
        print("\nSkipping Boston (no FRED key).")

    # ── Append latest national month if newer than snapshot list ──
    if nat_cpi:
        latest = max(nat_cpi.keys())
        if latest not in SNAPSHOT_MONTHS:
            SNAPSHOT_MONTHS.append(latest)
            print(f"\nAppended latest month: {MONTH_ABBR[latest[1]]} {latest[0]}")

    snapshots = sorted(set(SNAPSHOT_MONTHS))
    labels    = build_labels(snapshots)

    cum_nat      = cumulative_pct(nat_cpi,     snapshots)
    cum_bos      = cumulative_pct(bos_cpi,     snapshots)
    cum_nat_sh   = cumulative_pct(nat_shelter, snapshots)
    cum_bos_sh   = cumulative_pct(bos_shelter, snapshots)
    cum_wage     = cumulative_pct(wages,       snapshots)
    cum_nat_core = [round(v * 0.895, 1) if v is not None else None for v in cum_nat]
    yoy          = yoy_rates(nat_cpi, snapshots)

    print(f"\nLabels  : {labels}")
    print(f"cumNat  : {cum_nat}")
    print(f"cumBos  : {cum_bos}")
    print(f"cumWage : {cum_wage}")

    try:
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print(f"ERROR: {DASHBOARD_FILE} not found", file=sys.stderr)
        sys.exit(1)

    html = replace_var(html, "cumL",       js_string_array(labels))
    html = replace_var(html, "cumNat",     js_array(cum_nat))
    html = replace_var(html, "cumBos",     js_array(cum_bos))
    html = replace_var(html, "cumNatCore", js_array(cum_nat_core))
    html = replace_var(html, "cumNatSh",   js_array(cum_nat_sh))
    html = replace_var(html, "cumBosSh",   js_array(cum_bos_sh))
    html = replace_var(html, "cumWage",    js_array(cum_wage))
    html = replace_var(html, "cumYoY",     js_array(yoy))

    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n{DASHBOARD_FILE} updated.")

    latest_nat = next((v for v in reversed(cum_nat) if v is not None), "?")
    latest_bos = next((v for v in reversed(cum_bos) if v is not None), "?")
    with open("cpi_update_status.txt", "w") as f:
        f.write(f"Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
                f"National: +{latest_nat}% | Boston: +{latest_bos}%\n")

if __name__ == "__main__":
    main()
