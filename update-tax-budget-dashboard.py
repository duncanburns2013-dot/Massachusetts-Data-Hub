#!/usr/bin/env python3
"""
update-tax-budget-dashboard.py
Updates EIA electricity rates and BLS CPI data in
tax-budget-dashboard.html Cost of Living tab.
"""
import json, os, re, sys
from urllib.request import urlopen, Request
from datetime import datetime

EIA_KEY = os.environ.get("EIA_API_KEY", "").strip()
HTML_FILE = os.path.join(
    os.path.dirname(__file__),
    "tax-budget-dashboard.html"
)

if not os.path.exists(HTML_FILE):
    print(f"ERROR: {HTML_FILE} not found.")
    sys.exit(1)

# ── EIA electricity ──────────────────────────────────────────────────

def eia_fetch(state):
    if not EIA_KEY:
        return None, None
    base = "https://api.eia.gov/v2/electricity"
    path = "/retail-sales/data"
    params = (
        f"?api_key={EIA_KEY}"
        f"&frequency=monthly"
        f"&data[0]=price"
        f"&facets[sectorid][]=RES"
        f"&facets[stateid][]={state}"
        f"&sort[0][column]=period"
        f"&sort[0][direction]=desc"
        f"&length=1"
    )
    url = base + path + params
    try:
        req = Request(url, headers={"User-Agent": "X"})
        with urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        row = data["response"]["data"][0]
        return float(row["price"]), row["period"]
    except Exception as e:
        print(f"  EIA WARN ({state}): {e}")
        return None, None

# ── BLS CPI (free API v1, no key) ────────────────────────────────────

def bls_fetch_series(series_ids, start_year, end_year):
    """Fetch monthly CPI data from BLS API v1."""
    url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    payload = json.dumps({
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year)
    }).encode()
    req = Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "MA-Data-Hub/1.0"
        }
    )
    try:
        with urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        results = {}
        for series in data.get("Results", {}).get("series", []):
            sid = series["seriesID"]
            results[sid] = []
            for d in series.get("data", []):
                results[sid].append({
                    "year": int(d["year"]),
                    "period": d["period"],
                    "value": float(d["value"])
                })
        return results
    except Exception as e:
        print(f"  BLS ERROR: {e}")
        return {}

def compute_yoy(series_data):
    """Compute YoY % change from monthly index data.
    Returns (latest_yoy_pct, period_label) or (None, None)."""
    if not series_data or len(series_data) < 13:
        return None, None
    # Sort by year desc, period desc
    sorted_data = sorted(
        series_data,
        key=lambda x: (x["year"], x["period"]),
        reverse=True
    )
    latest = sorted_data[0]
    latest_val = latest["value"]
    latest_month = latest["period"]  # e.g. "M01"
    latest_year = latest["year"]

    # Find same month one year ago
    target_year = latest_year - 1
    year_ago = None
    for d in sorted_data:
        if d["year"] == target_year and d["period"] == latest_month:
            year_ago = d["value"]
            break

    if year_ago and year_ago > 0:
        yoy = round((latest_val - year_ago) / year_ago * 100, 1)
        month_num = int(latest_month.replace("M", ""))
        mnames = ["","Jan","Feb","Mar","Apr","May",
                  "Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        label = f"{mnames[month_num]} {latest_year}"
        return yoy, label
    return None, None

# ── Fetch everything ─────────────────────────────────────────────────

print("=== Tax/Budget Dashboard Auto-Update ===\n")

# EIA
print("Fetching EIA electricity rates...")
ma_elec, elec_period = eia_fetch("MA")
us_elec, _ = eia_fetch("US")
elec_label = ""
if elec_period:
    y, m = elec_period.split("-")
    mnames = ["","Jan","Feb","Mar","Apr","May",
              "Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    elec_label = f"{mnames[int(m)]} {y}"
print(f"  MA: {ma_elec}  US: {us_elec}  Period: {elec_label}")

# BLS CPI
print("\nFetching BLS CPI data (13 months)...")
now = datetime.now()
cpi_series = bls_fetch_series(
    [
        "CUSR0000SA0",     # US All Items
        "CUSR0100SA0",     # Northeast All Items
        "CUSR0000SAH1",    # US Shelter
        "CUSR0100SAH1",    # Northeast Shelter
    ],
    now.year - 1,
    now.year
)

us_cpi_yoy, cpi_label = compute_yoy(
    cpi_series.get("CUSR0000SA0", [])
)
ne_cpi_yoy, _ = compute_yoy(
    cpi_series.get("CUSR0100SA0", [])
)
us_shelter_yoy, _ = compute_yoy(
    cpi_series.get("CUSR0000SAH1", [])
)
ne_shelter_yoy, _ = compute_yoy(
    cpi_series.get("CUSR0100SAH1", [])
)

print(f"  US CPI: {us_cpi_yoy}%  NE CPI: {ne_cpi_yoy}%")
print(f"  US Shelter: {us_shelter_yoy}%  NE Shelter: {ne_shelter_yoy}%")
print(f"  Period: {cpi_label}")

# ── Read HTML and apply updates ──────────────────────────────────────

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()
original = html

def do_replace(html, old, new, label=""):
    if str(old) == str(new) or not old or not new:
        return html, 0
    count = html.count(str(old))
    if count > 0:
        html = html.replace(str(old), str(new))
        print(f"  {label}: '{old}' -> '{new}' ({count}x)")
    return html, count

# Electricity rate updates
if ma_elec and us_elec:
    new_prem = round((ma_elec - us_elec) / us_elec * 100)
    html, _ = do_replace(html, "31.5¢", f"{ma_elec:.1f}¢", "MA Elec")
    html, _ = do_replace(
        html, "31.5&#xA2;", f"{ma_elec:.1f}&#xA2;", "MA Elec HTML"
    )
    html, _ = do_replace(html, "18.05¢", f"{us_elec:.2f}¢", "US Elec")
    html, _ = do_replace(html, "+75%", f"+{new_prem}%", "Elec Premium")
    if elec_label:
        html, _ = do_replace(
            html, "Nov 2025", elec_label, "EIA Period"
        )

# CPI updates
if ne_cpi_yoy is not None:
    html, _ = do_replace(html, "+2.8%", f"+{ne_cpi_yoy}%", "NE CPI")
if us_cpi_yoy is not None:
    html, _ = do_replace(html, "+2.7%", f"+{us_cpi_yoy}%", "US CPI")
if ne_shelter_yoy is not None:
    html, _ = do_replace(
        html, "+4.0%", f"+{ne_shelter_yoy}%", "NE Shelter"
    )
if us_shelter_yoy is not None:
    html, _ = do_replace(
        html, "+3.6%", f"+{us_shelter_yoy}%", "US Shelter"
    )

# Update BLS period labels
if cpi_label:
    html, _ = do_replace(
        html, "BLS Nov 2025", f"BLS {cpi_label}", "BLS Period"
    )
    html, _ = do_replace(
        html, "(BLS Nov 2025)", f"(BLS {cpi_label})", "BLS Period 2"
    )
    html, _ = do_replace(
        html, "BLS (Nov 2025)", f"BLS ({cpi_label})", "BLS Period 3"
    )

# ── Write ─────────────────────────────────────────────────────────────

if html != original:
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nDone - updated {HTML_FILE}")
else:
    print("\nNo changes - data is current.")
