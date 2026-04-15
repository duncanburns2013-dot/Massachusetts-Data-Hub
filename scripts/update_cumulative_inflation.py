#!/usr/bin/env python3
"""
update_cumulative_inflation.py  (v2 — fixed base-month lookup)
"""

import json
import os
import re
import sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

DASHBOARD_FILE = "tax-budget-dashboard.html"
BLS_API_URL    = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BASE_YEAR      = 2021
BASE_MONTH     = 1

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

SERIES_IDS = {
    "nat_cpi":    "CPIAUCSL",
    "bos_cpi":    "CUURA103SA0",
    "nat_shelter":"CUSR0000SAH",
    "bos_shelter":"CUURA103SAH",
    "wages":      "CES0500000003",
}

def fetch_bls(series_list, start_year=2020, end_year=None):
    if end_year is None:
        end_year = datetime.now().year

    api_key = os.environ.get("BLS_API_KEY", "")

    payload = {
        "seriesid":      series_list,
        "startyear":     str(start_year),
        "endyear":       str(end_year),
        "catalog":       False,
        "calculations":  False,
        "annualaverage": False,
    }
    if api_key:
        payload["registrationkey"] = api_key

    body = json.dumps(payload).encode("utf-8")
    req  = Request(BLS_API_URL, data=body,
                   headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"BLS API status: {result.get('status')}")
            for msg in result.get("message", []):
                print(f"  BLS message: {msg}")
            return result
    except URLError as e:
        print(f"ERROR: BLS API request failed — {e}", file=sys.stderr)
        sys.exit(1)

def parse_series(bls_response, series_id):
    for series in bls_response.get("Results", {}).get("series", []):
        if series["seriesID"] != series_id:
            continue
        result = {}
        for obs in series.get("data", []):
            period = obs["period"]
            if not period.startswith("M") or period == "M13":
                continue
            month = int(period[1:])
            year  = int(obs["year"])
            try:
                result[(year, month)] = float(obs["value"])
            except ValueError:
                pass
        if result:
            keys = sorted(result.keys())
            print(f"  {series_id}: {len(result)} obs, "
                  f"range {keys[0][0]}-{keys[0][1]:02d} to {keys[-1][0]}-{keys[-1][1]:02d}")
            base_val = result.get((BASE_YEAR, BASE_MONTH))
            print(f"  {series_id}: base (2021-01) = {base_val}")
        else:
            print(f"  {series_id}: NO DATA RETURNED", file=sys.stderr)
        return result
    print(f"  {series_id}: series ID not found in response", file=sys.stderr)
    return {}

def cumulative_pct(index_map, snapshots, base_year=BASE_YEAR, base_month=BASE_MONTH):
    base = index_map.get((base_year, base_month))
    if base is None:
        print(f"WARNING: base {base_year}-{base_month:02d} missing", file=sys.stderr)
        return [None] * len(snapshots)

    result = []
    for (yr, mo) in snapshots:
        val = index_map.get((yr, mo))
        if val is None:
            for delta in (1, -1, 2, -2):
                adj_mo = mo + delta
                if 1 <= adj_mo <= 12:
                    val = index_map.get((yr, adj_mo))
                    if val is not None:
                        break
        result.append(round((val - base) / base * 100, 1) if val is not None else None)
    return result

def yoy_rates(index_map, snapshots):
    result = []
    for (yr, mo) in snapshots:
        curr = index_map.get((yr, mo))
        prev = index_map.get((yr - 1, mo))
        if curr is None or prev is None:
            result.append(None)
        else:
            result.append(round((curr - prev) / prev * 100, 1))
    return result

def build_labels(snapshots):
    return [f"{MONTH_ABBR[mo]} {str(yr)[2:]}" for yr, mo in snapshots]

def js_array(values):
    return "[" + ",".join("null" if v is None else str(v) for v in values) + "]"

def js_string_array(values):
    return "[" + ",".join(f"'{v}'" for v in values) + "]"

def replace_var(html, varname, new_literal):
    pattern = rf"(var\s+{re.escape(varname)}\s*=\s*)\[[^\]]*\]"
    new_html, count = re.subn(pattern, rf"\g<1>{new_literal}", html,
                               count=1, flags=re.DOTALL)
    if count == 0:
        print(f"WARNING: 'var {varname}' not found in HTML — skipped", file=sys.stderr)
    return new_html

def main():
    print("Fetching BLS data...")
    response = fetch_bls(list(SERIES_IDS.values()))

    if response.get("status") != "REQUEST_SUCCEEDED":
        print(f"ERROR: BLS status = {response.get('status')}", file=sys.stderr)
        sys.exit(1)

    print("\nParsing series:")
    nat_cpi     = parse_series(response, SERIES_IDS["nat_cpi"])
    bos_cpi     = parse_series(response, SERIES_IDS["bos_cpi"])
    nat_shelter = parse_series(response, SERIES_IDS["nat_shelter"])
    bos_shelter = parse_series(response, SERIES_IDS["bos_shelter"])
    wages       = parse_series(response, SERIES_IDS["wages"])

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

    print(f"\nLabels: {labels}")
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
                f"National cumulative: +{latest_nat}% | Boston: +{latest_bos}%\n")

if __name__ == "__main__":
    main()
