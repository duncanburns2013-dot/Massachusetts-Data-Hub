#!/usr/bin/env python3
"""
update-energy-dashboard.py
Fetches latest EIA electricity rates and updates energy-dashboard.html directly.
"""
import json, os, re, sys
from urllib.request import urlopen, Request

API_KEY = os.environ.get("EIA_API_KEY", "").strip()
if not API_KEY:
    print("Set EIA_API_KEY env variable.")
    sys.exit(1)

HTML_FILE = os.path.join(os.path.dirname(__file__), "energy-dashboard.html")

def eia_fetch(state):
    url = f"https://api.eia.gov/v2/electricity/retail-sales/data?api_key={API_KEY}&frequency=monthly&data[0]=price&facets[sectorid][]=RES&facets[stateid][]={state}&sort[0][column]=period&sort[0][direction]=desc&length=1"
    try:
        with urlopen(Request(url, headers={"User-Agent": "MA-Data-Hub/1.0"}), timeout=20) as r:
            data = json.loads(r.read())
        row = data["response"]["data"][0]
        return float(row["price"]), row["period"]
    except Exception as e:
        print(f"  WARN: Could not fetch {state}: {e}")
        return None, None

print("Fetching latest EIA electricity rates...")
states = {"MA": None, "US": None, "RI": None, "CT": None, "NY": None, "FL": None, "TX": None, "LA": None}
period = None
for st in states:
    rate, p = eia_fetch(st)
    if rate:
        states[st] = round(rate, 2)
        if st == "MA":
            period = p
    print(f"  {st}: {states[st]} cents/kWh")

if not states["MA"] or not states["US"]:
    print("ERROR: Could not fetch MA or US rates. Aborting.")
    sys.exit(1)

ma = states["MA"]
us = states["US"]
prem = round((ma - us) / us * 100)
overpay = round((ma - us) / 100 * 7200)
period_label = ""
if period:
    y, m = period.split("-")
    months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    period_label = f"EIA {months[int(m)]} {y}"

print(f"\nMA: {ma} cents  US: {us} cents  Premium: +{prem}%  Overpay: ${overpay}/yr  Period: {period_label}")

if not os.path.exists(HTML_FILE):
    print(f"ERROR: {HTML_FILE} not found.")
    sys.exit(1)

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()
original = html

elec_ma_match = re.search(r"const ELEC_MA\s*=\s*\[([^\]]+)\]", html)
elec_us_match = re.search(r"const ELEC_US\s*=\s*\[([^\]]+)\]", html)

if elec_ma_match and elec_us_match:
    old_ma_vals = [v.strip() for v in elec_ma_match.group(1).split(",")]
    old_us_vals = [v.strip() for v in elec_us_match.group(1).split(",")]
    new_ma_vals = old_ma_vals[:-1] + [str(ma)]
    new_us_vals = old_us_vals[:-1] + [str(us)]
    html = html.replace(f"const ELEC_MA = [{elec_ma_match.group(1)}]", f"const ELEC_MA = [{','.join(new_ma_vals)}]")
    html = html.replace(f"const ELEC_US = [{elec_us_match.group(1)}]", f"const ELEC_U
