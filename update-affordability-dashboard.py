#!/usr/bin/env python3
"""
update-affordability-dashboard.py
Fetches latest BLS + EIA data and updates affordability-dashboard.html directly.
"""
import json, os, re, sys
from urllib.request import urlopen, Request
from datetime import datetime

EIA_KEY = os.environ.get("EIA_API_KEY", "").strip()
HTML_FILE = os.path.join(os.path.dirname(__file__), "affordability-dashboard.html")

if not os.path.exists(HTML_FILE):
    print(f"ERROR: {HTML_FILE} not found.")
    sys.exit(1)

def bls_fetch(series_ids):
    url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    payload = json.dumps({"seriesid": series_ids, "latest": True}).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "MA-Data-Hub/1.0"})
    try:
        with urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        results = {}
        for series in data.get("Results", {}).get("series", []):
            sid = series["seriesID"]
            if series["data"]:
                d = series["data"][0]
                results[sid] = {"value": d["value"], "year": d["year"], "period": d["period"], "periodName": d.get("periodName", "")}
        return results
    except Exception as e:
        print(f"  BLS ERROR: {e}")
        return {}

def eia_fetch(state):
    if not EIA_KEY:
        return None, None
    url = f"https://api.eia.gov/v2/electricity/retail-sales/data?api_key={EIA_KEY}&frequency=monthly&data[0]=price&facets[sectorid][]=RES&facets[stateid][]={state}&sort[0][column]=period&sort[0][direction]=desc&length=1"
    try:
        with urlopen(Request(url, headers={"User-Agent": "MA-Data-Hub/1.0"}), timeout=20) as r:
            data = json.loads(r.read())
        row = data["response"]["data"][0]
        return float(row["price"]), row["period"]
    except Exception as e:
        print(f"  EIA WARN ({state}): {e}")
        return None, None

print("=== Affordability Dashboard Auto-Update ===\n")

print("Fetching BLS data...")
bls = bls_fetch(["LASST250000000000003", "LNS14000000"])
ma_unemp = bls.get("LASST250000000000003", {})
us_unemp = bls.get("LNS14000000", {})
print(f"  MA unemployment: {ma_unemp.get('value', 'N/A')}% ({ma_unemp.get('periodName', '')} {ma_unemp.get('year', '')})")
print(f"  US unemployment: {us_unemp.get('value', 'N/A')}%")

print("\nFetching EIA electricity rates...")
ma_elec, elec_period = eia_fetch("MA")
us_elec, _ = eia_fetch("US")
print(f"  MA: {ma_elec}¢/kWh  US: {us_elec}¢/kWh  Period: {elec_period}")

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()
original = html

def do_replace(html, old, new, label=""):
    if old == new or not old or not new:
        return html, 0
    count = html.count(str(old))
    if count > 0:
        html = html.replace(str(old), str(new))
        print(f"  {label}: '{old}' -> '{new}' ({count}x)")
    return html, count

# Unemployment updates
if ma_unemp.get("value"):
    new_ma = ma_unemp["value"]
    unemp_match = re.search(r'Unemployment.*?(\d+\.\d+)%', html[:3000])
    if unemp_match:
        old_val = unemp_match.group(1)
        if old_val != new_ma:
            html, _ = do_replace(html, f"{old_val}%", f"{new_ma}%", "MA Unemployment")
    if us_unemp.get("value"):
        new_delta = round(float(new_ma) - float(us_unemp["value"]), 1)
        sign = "+" if new_delta >= 0 else ""
        delta_match = re.search(r'vs National.*?([+\-]\d+\.\d+)%', html[:3000])
        if delta_match:
            html, _ = do_replace(html, f"{delta_match.group(1)}%", f"{sign}{new_delta}%", "Unemp Delta")

# Electricity updates
if ma_elec and us_elec:
    new_prem = round((ma_elec - us_elec) / us_elec * 100)
    extra_annual = round((ma_elec - us_elec) / 100 * 7200)
    extra_monthly = round((ma_elec - us_elec) / 100 * 600)

    old_ma_matches = re.findall(r'(\d{2}\.\d{2})¢', html)
    if old_ma_matches:
        from collections import Counter
        counts = Counter(old_ma_matches)
        ma_rates = [(v, c) for v, c in counts.items() if float(v) > 25]
        us_rates = [(v, c) for v, c in counts.items() if 15 < float(v) < 25]
        if ma_rates:
            old_ma = max(ma_rates, key=lambda x: x[1])[0]
            html, _ = do_replace(html, f"{old_ma}¢", f"{ma_elec:.2f}¢", "MA Elec")
        if us_rates:
            old_us = max(us_rates, key=lambda x: x[1])[0]
            html, _ = do_replace(html, f"{old_us}¢", f"{us_elec:.2f}¢", "US Elec")

    if elec_period:
        y, m = elec_period.split("-")
        months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        new_label = f"{months[int(m)]} {y}"
        html, _ = do_replace(html, "Jan 2026", new_label, "EIA Period")

# Update date
today = datetime.now().strftime("%B %d, %Y")
date_match = re.search(r'Last Updated:.*?(\w+ \d+, \d{4})', html)
if date_match:
    html, _ = do_replace(html, date_match.group(1), today, "Last Updated")

if html != original:
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✓ Updated {HTML_FILE}")
else:
    print("\nNo changes needed.")
