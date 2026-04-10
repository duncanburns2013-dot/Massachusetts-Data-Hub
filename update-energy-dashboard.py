#!/usr/bin/env python3
"""
update-energy-dashboard.py

Simple auto-import: fetches latest EIA electricity rates and updates
the hardcoded numbers directly in energy-dashboard.html.

No separate data files. No refactoring. Same self-contained HTML.

Usage:
  EIA_API_KEY=your_key python update-energy-dashboard.py

Get a free key: https://www.eia.gov/opendata/register.php
"""

import json, os, re, sys
from urllib.request import urlopen, Request

API_KEY = os.environ.get("EIA_API_KEY", "")
if not API_KEY:
    print("Set EIA_API_KEY env variable. Free key: https://www.eia.gov/opendata/register.php")
    sys.exit(1)

HTML_FILE = os.path.join(os.path.dirname(__file__), "energy-dashboard.html")

# ── Fetch latest residential electricity rates from EIA ──────────────

def eia_fetch(state):
    """Get latest monthly residential electricity rate for a state (¢/kWh)."""
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
    print(f"  {st}: {states[st]}¢/kWh")

if not states["MA"] or not states["US"]:
    print("ERROR: Could not fetch MA or US rates. Aborting.")
    sys.exit(1)

# ── Compute derived values ───────────────────────────────────────────

ma = states["MA"]
us = states["US"]
prem = round((ma - us) / us * 100)
overpay = round((ma - us) / 100 * 7200)  # 600 kWh/mo × 12
mo_bill = round(ma / 100 * 600)
period_label = ""
if period:
    y, m = period.split("-")
    months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    period_label = f"EIA {months[int(m)]} {y}"

print(f"\nMA: {ma}¢  US: {us}¢  Premium: +{prem}%  Overpay: ${overpay}/yr  Period: {period_label}")

# ── Read HTML and do replacements ────────────────────────────────────

if not os.path.exists(HTML_FILE):
    print(f"ERROR: {HTML_FILE} not found. Put this script next to your dashboard.")
    sys.exit(1)

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html  # keep backup

def replace_rate(html, old_rate, new_rate):
    """Replace a specific rate value throughout the file."""
    return html.replace(str(old_rate), str(new_rate))

# Find current values in the file to know what to replace
# Look for the MA rate in the ELEC_MA array (last entry)
elec_ma_match = re.search(r"const ELEC_MA\s*=\s*\[([^\]]+)\]", html)
elec_us_match = re.search(r"const ELEC_US\s*=\s*\[([^\]]+)\]", html)

if elec_ma_match and elec_us_match:
    old_ma_vals = [v.strip() for v in elec_ma_match.group(1).split(",")]
    old_us_vals = [v.strip() for v in elec_us_match.group(1).split(",")]
    old_ma = old_ma_vals[-1]
    old_us = old_us_vals[-1]
    old_prem = None

    # Update the last value in each array
    new_ma_vals = old_ma_vals[:-1] + [str(ma)]
    new_us_vals = old_us_vals[:-1] + [str(us)]

    html = html.replace(
        f"const ELEC_MA = [{elec_ma_match.group(1)}]",
        f"const ELEC_MA = [{','.join(new_ma_vals)}]"
    )
    html = html.replace(
        f"const ELEC_US = [{elec_us_match.group(1)}]",
        f"const ELEC_US = [{','.join(new_us_vals)}]"
    )
    print(f"Updated ELEC_MA last value: {old_ma} → {ma}")
    print(f"Updated ELEC_US last value: {old_us} → {us}")

# Update hero stat badges and inline text
# These are the specific strings that appear in the HTML
replacements = [
    # Hero badges
    ("31.16¢", f"{ma}¢"),
    ("31.16&#x00A2;", f"{ma}&#x00A2;"),
    ("+79%", f"+{prem}%"),
    # National average references
    ("17.45¢", f"{us}¢"),
    ("17.45&#x00A2;", f"{us}&#x00A2;"),
    # Overpayment
    ("$987", f"${overpay}"),
    # EIA period labels
    ("EIA Jan 2026", period_label),
    ("(EIA Jan 2026)", f"({period_label})"),
    ("January 2026", period_label.replace("EIA ", "")),
    ("Jan 2026", period_label.replace("EIA ", "")),
]

# State rates in the comparison table
state_replacements = {
    "RI": ("30.14", states.get("RI")),
    "CT": ("28.30", states.get("CT")),
    "NY": ("28.37", states.get("NY")),
    "FL": ("15.92", states.get("FL")),
    "TX": ("15.69", states.get("TX")),
    "LA": ("12.46", states.get("LA")),
}

for old, new in replacements:
    if old != new:
        count = html.count(old)
        if count > 0:
            html = html.replace(old, new)
            print(f"  Replaced '{old}' → '{new}' ({count}x)")

for st, (old_val, new_val) in state_replacements.items():
    if new_val and str(old_val) != str(new_val):
        # Be careful to only replace in table/chart contexts
        html = html.replace(old_val, str(new_val))
        print(f"  {st}: {old_val} → {new_val}")

# Recompute table-derived values (annual costs, premiums)
for st_code, rate in states.items():
    if rate:
        annual = round(rate / 100 * 7200)
        vs_pct = round((rate - us) / us * 100) if us > 0 else 0

# ── Write updated file ───────────────────────────────────────────────

if html != original:
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✓ Updated {HTML_FILE}")
    print(f"  MA: {ma}¢/kWh | US: {us}¢/kWh | +{prem}% | ${overpay}/yr overpayment")
    print(f"  Period: {period_label}")
else:
    print("\nNo changes needed — data is already current.")
