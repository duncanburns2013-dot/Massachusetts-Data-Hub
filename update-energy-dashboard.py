#!/usr/bin/env python3
"""update-energy-dashboard.py — auto-update EIA rates in energy-dashboard.html"""
import json, os, re, sys
from urllib.request import urlopen, Request

API_KEY = os.environ.get("EIA_API_KEY", "").strip()
if not API_KEY:
    print("Set EIA_API_KEY env variable.")
    sys.exit(1)

HTML_FILE = os.path.join(
    os.path.dirname(__file__),
    "energy-dashboard.html"
)

def eia_fetch(state):
    base = "https://api.eia.gov/v2/electricity"
    path = "/retail-sales/data"
    params = (
        f"?api_key={API_KEY}"
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
        print(f"  WARN {state}: {e}")
        return None, None

print("Fetching EIA electricity rates...")
codes = ["MA","US","RI","CT","NY","FL","TX","LA"]
rates = {}
period = None
for st in codes:
    rate, p = eia_fetch(st)
    if rate:
        rates[st] = round(rate, 2)
        if st == "MA":
            period = p
    print(f"  {st}: {rates.get(st)} c/kWh")

ma = rates.get("MA")
us = rates.get("US")
if not ma or not us:
    print("ERROR: Could not fetch MA or US.")
    sys.exit(1)

prem = round((ma - us) / us * 100)
overpay = round((ma - us) / 100 * 7200)
plabel = ""
if period:
    y, m = period.split("-")
    mnames = ["","Jan","Feb","Mar","Apr","May",
              "Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    plabel = f"EIA {mnames[int(m)]} {y}"

print(f"\nMA:{ma} US:{us} +{prem}% ${overpay}/yr {plabel}")

if not os.path.exists(HTML_FILE):
    print(f"ERROR: {HTML_FILE} not found.")
    sys.exit(1)

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()
original = html

# Update JS arrays
for name, val in [("ELEC_MA", ma), ("ELEC_US", us)]:
    pat = re.compile(r"const " + name + r"\s*=\s*\[([^\]]+)\]")
    match = pat.search(html)
    if match:
        vals = [v.strip() for v in match.group(1).split(",")]
        vals[-1] = str(val)
        old = f"const {name} = [{match.group(1)}]"
        new = f"const {name} = [{','.join(vals)}]"
        html = html.replace(old, new)
        print(f"  Updated {name} array")

# Find-and-replace display values
swaps = [
    ("31.16¢", f"{ma}¢"),
    ("31.16&#x00A2;", f"{ma}&#x00A2;"),
    ("+79%", f"+{prem}%"),
    ("17.45¢", f"{us}¢"),
    ("17.45&#x00A2;", f"{us}&#x00A2;"),
    ("$987", f"${overpay}"),
    ("EIA Jan 2026", plabel),
    ("(EIA Jan 2026)", f"({plabel})"),
    ("Jan 2026", plabel.replace("EIA ", "")),
]

for old, new in swaps:
    if old != new:
        n = html.count(old)
        if n > 0:
            html = html.replace(old, new)
            print(f"  '{old}' -> '{new}' ({n}x)")

# State rates
st_swaps = {"RI":"30.14","CT":"28.30","NY":"28.37",
            "FL":"15.92","TX":"15.69","LA":"12.46"}
for st, old_val in st_swaps.items():
    new_val = rates.get(st)
    if new_val and old_val != str(new_val):
        html = html.replace(old_val, str(new_val))
        print(f"  {st}: {old_val} -> {new_val}")

if html != original:
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nDone - updated {HTML_FILE}")
else:
    print("\nNo changes - data is current.")
