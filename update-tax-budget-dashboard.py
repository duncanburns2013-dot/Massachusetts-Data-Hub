#!/usr/bin/env python3
"""update-tax-budget-dashboard.py — updates EIA + BLS data in tax-budget-dashboard.html"""
import json, os, re, sys
from urllib.request import urlopen, Request
from datetime import datetime

EIA_KEY = os.environ.get("EIA_API_KEY", "").strip()
HTML_FILE = os.path.join(os.path.dirname(__file__), "tax-budget-dashboard.html")
if not os.path.exists(HTML_FILE):
    print(f"ERROR: {HTML_FILE} not found.")
    sys.exit(1)

def eia_fetch(state):
    if not EIA_KEY:
        return None, None
    base = "https://api.eia.gov/v2/electricity"
    path = "/retail-sales/data"
    params = (f"?api_key={EIA_KEY}&frequency=monthly&data[0]=price"
              f"&facets[sectorid][]=RES&facets[stateid][]={state}"
              f"&sort[0][column]=period&sort[0][direction]=desc&length=1")
    try:
        with urlopen(Request(base+path+params, headers={"User-Agent":"X"}), timeout=20) as r:
            data = json.loads(r.read())
        row = data["response"]["data"][0]
        return float(row["price"]), row["period"]
    except Exception as e:
        print(f"  EIA WARN ({state}): {e}")
        return None, None

def bls_cpi(series_ids, start_yr, end_yr):
    url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    payload = json.dumps({"seriesid": series_ids, "startyear": str(start_yr), "endyear": str(end_yr)}).encode()
    try:
        with urlopen(Request(url, data=payload, headers={"Content-Type":"application/json","User-Agent":"X"}), timeout=20) as r:
            data = json.loads(r.read())
        out = {}
        for s in data.get("Results",{}).get("series",[]):
            out[s["seriesID"]] = [(int(d["year"]), d["period"], float(d["value"])) for d in s.get("data",[])]
        return out
    except Exception as e:
        print(f"  BLS ERROR: {e}")
        return {}

def yoy(data):
    if not data or len(data) < 13:
        return None, None
    s = sorted(data, key=lambda x:(x[0],x[1]), reverse=True)
    latest = s[0]
    for d in s:
        if d[0] == latest[0]-1 and d[1] == latest[1]:
            pct = round((latest[2]-d[2])/d[2]*100, 1)
            mn = int(latest[1].replace("M",""))
            names = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            return pct, f"{names[mn]} {latest[0]}"
    return None, None

print("=== Tax/Budget Dashboard Update ===\n")
print("Fetching EIA...")
ma_e, ep = eia_fetch("MA")
us_e, _ = eia_fetch("US")
el = ""
if ep:
    y,m = ep.split("-")
    names = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    el = f"{names[int(m)]} {y}"
print(f"  MA:{ma_e} US:{us_e} Period:{el}")

print("Fetching BLS CPI...")
now = datetime.now()
cpi = bls_cpi(["CUSR0000SA0","CUSR0100SA0","CUSR0000SAH1","CUSR0100SAH1"], now.year-1, now.year)
us_cpi, cl = yoy(cpi.get("CUSR0000SA0",[]))
ne_cpi, _ = yoy(cpi.get("CUSR0100SA0",[]))
us_sh, _ = yoy(cpi.get("CUSR0000SAH1",[]))
ne_sh, _ = yoy(cpi.get("CUSR0100SAH1",[]))
print(f"  US CPI:{us_cpi}% NE CPI:{ne_cpi}% US Shelter:{us_sh}% NE Shelter:{ne_sh}%")

with open(HTML_FILE,"r",encoding="utf-8") as f:
    html = f.read()
orig = html

def rep(html, old, new, lbl=""):
    if str(old)==str(new) or not old or not new: return html
    n = html.count(str(old))
    if n > 0:
        html = html.replace(str(old), str(new))
        print(f"  {lbl}: '{old}'->'{new}' ({n}x)")
    return html

if ma_e and us_e:
    prem = round((ma_e-us_e)/us_e*100)
    html = rep(html, "31.5¢", f"{ma_e:.1f}¢", "MA Elec")
    html = rep(html, "31.5&#x00A2;", f"{ma_e:.1f}&#x00A2;", "MA Elec2")
    html = rep(html, "18.05¢", f"{us_e:.2f}¢", "US Elec")
    html = rep(html, "18.05&#x00A2;", f"{us_e:.2f}&#x00A2;", "US Elec2")
    html = rep(html, "+75%", f"+{prem}%", "Elec Prem")
    if el:
        html = rep(html, "Nov 2025", el, "EIA Period")

if ne_cpi is not None: html = rep(html, "+2.8%", f"+{ne_cpi}%", "NE CPI")
if us_cpi is not None: html = rep(html, "+2.7%", f"+{us_cpi}%", "US CPI")
if ne_sh is not None: html = rep(html, "+4.0%", f"+{ne_sh}%", "NE Shelter")
if us_sh is not None: html = rep(html, "+3.6%", f"+{us_sh}%", "US Shelter")
if cl: html = rep(html, "BLS Nov 2025", f"BLS {cl}", "BLS Period")

if html != orig:
    with open(HTML_FILE,"w",encoding="utf-8") as f:
        f.write(html)
    print(f"\nDone - updated {HTML_FILE}")
else:
    print("\nNo changes needed.")
