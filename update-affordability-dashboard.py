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

# Counts how many DATA figures actually moved. The "Last Updated" stamp below is
# gated on this: stamping the run date unconditionally rewrote the file on every
# run, so `html != original` was always true and the page committed daily -- looking
# freshly maintained while most of the replacements below silently matched nothing.
data_changes = 0

# Unemployment updates
if ma_unemp.get("value"):
    new_ma = ma_unemp["value"]
    # Target the Unemployment stat card by its own markup, and rewrite only inside
    # that card. The old anchor searched html[:3000] for /Unemployment.*?(\d+\.\d+)%/
    # -- but the first "Unemployment" sits at index ~12,138, and it is the hero
    # "#44 Unemployment Rank" card, not the rate. So the search never matched, the
    # card sat on Dec 2025 for 7 months, and nothing said so.
    #
    # It also replaced the bare string "4.8%" everywhere in the file, which would
    # have clobbered any unrelated figure that happened to share the value. Scoped
    # to the card now.
    card_re = re.compile(
        r'(<div class="label">Unemployment</div><div class="value[^"]*">)(\d+\.\d+)%'
        r'(</div><div class="sub">)([^<]*)(</div>)'
    )
    card = card_re.search(html)
    if card:
        old_val, old_sub = card.group(2), card.group(4)
        # Keep the card's own "December 2025" subtitle honest about which month the
        # value is from -- it drifted 7 months precisely because the rate and its
        # vintage label were maintained separately.
        new_sub = f"{ma_unemp.get('periodName','')} {ma_unemp.get('year','')}".strip() or old_sub
        if old_val != str(new_ma) or old_sub != new_sub:
            html = card_re.sub(
                lambda m: f"{m.group(1)}{new_ma}%{m.group(3)}{new_sub}{m.group(5)}",
                html, count=1,
            )
            print(f"  MA Unemployment: '{old_val}% ({old_sub})' -> '{new_ma}% ({new_sub})'")
            data_changes += 1
    else:
        print("  !! MA Unemployment: stat-card anchor not found -- NOT updated")
    if us_unemp.get("value"):
        new_delta = round(float(new_ma) - float(us_unemp["value"]), 1)
        sign = "+" if new_delta >= 0 else ""
        delta_match = re.search(r'vs National.*?([+\-]\d+\.\d+)%', html[:3000])
        if delta_match:
            html, n = do_replace(html, f"{delta_match.group(1)}%", f"{sign}{new_delta}%", "Unemp Delta")
            data_changes += n
        else:
            print("  !! Unemp Delta: 'vs National' anchor not found -- NOT updated")

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
            html, n = do_replace(html, f"{old_ma}¢", f"{ma_elec:.2f}¢", "MA Elec")
            data_changes += n
        if us_rates:
            old_us = max(us_rates, key=lambda x: x[1])[0]
            html, n = do_replace(html, f"{old_us}¢", f"{us_elec:.2f}¢", "US Elec")
            data_changes += n

    if elec_period:
        y, m = elec_period.split("-")
        months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        new_label = f"{months[int(m)]} {y}"
        # Anchored on a literal month, so the first successful run ate its own anchor
        # and the label has been frozen ever since while the rates beside it kept
        # moving. Match whatever month label is actually there instead.
        period_match = re.search(r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) 20\d{2})\b', html)
        if period_match and period_match.group(1) != new_label:
            html, n = do_replace(html, period_match.group(1), new_label, "EIA Period")
            data_changes += n
        elif not period_match:
            print("  !! EIA Period: no month label found -- NOT updated")

# Only stamp the date if real data moved. A run that changed nothing must leave the
# file untouched so it does not advertise a freshness it does not have, and so a
# dead anchor shows up as an absent commit instead of a daily green one.
if data_changes > 0:
    today = datetime.now().strftime("%B %d, %Y")
    date_match = re.search(r'Last Updated:.*?(\w+ \d+, \d{4})', html)
    if date_match:
        html, _ = do_replace(html, date_match.group(1), today, "Last Updated")
else:
    print("\n!! No data figures changed -- leaving the date stamp alone.")
    print("   If this repeats every run, an anchor has gone stale: the page is")
    print("   frozen, not current. Check the '!!' lines above.")

if html != original:
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✓ Updated {HTML_FILE} ({data_changes} data figure(s) changed)")
else:
    print("\nNo changes needed.")
