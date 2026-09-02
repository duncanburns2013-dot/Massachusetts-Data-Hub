#!/usr/bin/env python3
"""update-fuel-prices.py — refresh the fuel series on energy-dashboard.html from EIA.

WHY THIS EXISTS
---------------
The page auto-maintained its electricity series (update-energy-dashboard.py) and
hand-maintained everything else. Audited 2026-08-07 against EIA's own published
series, every hand-typed fuel array had drifted:

  GAS_MA     2025 read 2.97 vs EIA 3.131; 8 of 16 years out by >=5c
  GAS_US     out by 9-13c in ELEVEN of 16 years -- a consistent bias, so it was
             transcribed from something that was not this series
  DIESEL_NE  2021 out by 27.6c; 2025 out by 19.3c
  MA_NG      2023 out by 59c/therm
  US_NG      2025 read 1.25 vs EIA 1.80 -- which alone doubled the natural-gas
             premium the Equivalence tab bills against ($945 vs $469)

Worse than any single value: MA_GAS_TODAY was GAS_MA[last] -- the 2025 ANNUAL
AVERAGE relabelled "today". The tab billed gasoline at $2.97 while Massachusetts
was paying $4.22. An annual average is not a current price, so this script
writes the two separately and the page keeps them separate.

WHAT IT WRITES
--------------
  GAS_MA / GAS_US / DIESEL_US / DIESEL_NE   annual averages, $/gal
  MA_NG / US_NG                             annual averages, $/therm
  FUEL_NOW                                  latest weekly retail prices + as-of

Annual arrays cover COMPLETE calendar years only and must stay the same length
as the page's YEARS array -- update-energy-dashboard.py asserts that for the
electricity series, and a mismatch here would silently misalign every chart.
The current partial year never enters an annual average; it belongs in FUEL_NOW.

Requires EIA_API_KEY (same repo secret the electricity updater uses).
"""
import collections
import datetime
import json
import os
import re
import ssl
import statistics as st
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_KEY = os.environ.get("EIA_API_KEY", "").strip()
if not API_KEY:
    sys.exit("ERROR: set the EIA_API_KEY environment variable.")

HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "energy-dashboard.html")
PETRO = "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
NATGAS = "https://api.eia.gov/v2/natural-gas/pri/sum/data/"

# 1 Mcf of pipeline gas is ~1.037 MMBtu = ~10.37 therms. EIA publishes
# residential gas in $/Mcf; the page bills in $/therm at a 700-therm convention.
THERMS_PER_MCF = 10.37

# (page array, EIA series id, endpoint, frequency, decimals, divisor)
SERIES = [
    ("GAS_MA",    "EMM_EPM0_PTE_SMA_DPG", PETRO,  "weekly",  3, 1.0),
    ("GAS_US",    "EMM_EPM0_PTE_NUS_DPG", PETRO,  "weekly",  3, 1.0),
    ("DIESEL_US", "EMD_EPD2D_PTE_NUS_DPG", PETRO, "weekly",  3, 1.0),
    ("DIESEL_NE", "EMD_EPD2D_PTE_R1X_DPG", PETRO, "weekly",  3, 1.0),
    ("MA_NG",     "N3010MA3",             NATGAS, "monthly", 2, THERMS_PER_MCF),
    ("US_NG",     "N3010US3",             NATGAS, "monthly", 2, THERMS_PER_MCF),
]

_CTX = ssl.create_default_context()
if os.environ.get("PIPELINE_INSECURE_TLS") == "1":
    # Only for the TLS-inspecting proxy on the author's machine. CI verifies.
    _CTX.check_hostname = False
    _CTX.verify_mode = ssl.CERT_NONE


def fetch(url, series, frequency, tries=5):
    """All observations for one EIA series, newest first, as (date, value)."""
    q = [("api_key", API_KEY), ("frequency", frequency), ("data[0]", "value"),
         ("facets[series][]", series), ("sort[0][column]", "period"),
         ("sort[0][direction]", "desc"), ("length", "5000")]
    full = url + "?" + urllib.parse.urlencode(q)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(full, timeout=90, context=_CTX) as r:
                body = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            sys.exit(f"ERROR: EIA {series} -> HTTP {e.code}: "
                     f"{e.read().decode('utf-8', 'replace')[:200]}")
        except (urllib.error.URLError, TimeoutError) as e:
            # TimeoutError is NOT a URLError: a read timeout escaped this handler
            # entirely and aborted the run. Same defect as update-energy-dashboard.py.
            if attempt < tries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            sys.exit(f"ERROR: EIA {series} unreachable: {e}")
    rows = []
    for d in body.get("response", {}).get("data", []):
        v = d.get("value")
        if v in (None, ""):
            continue
        rows.append((d["period"], float(v)))
    if not rows:
        sys.exit(f"ERROR: EIA returned no observations for {series}.")
    return sorted(rows)


def annual(rows, years, dp, divisor):
    by = collections.defaultdict(list)
    for period, v in rows:
        by[int(period[:4])].append(v / divisor)
    out = []
    for y in years:
        if y not in by:
            sys.exit(f"ERROR: EIA has no data for {y}; cannot fill the array.")
        out.append(round(st.mean(by[y]), dp))
    return out


def sub(html, pattern, replacement, what):
    new, n = re.subn(pattern, lambda _: replacement, html, count=1)
    if not n:
        sys.exit(f"ERROR: anchor for {what} not found -- page structure changed. "
                 f"Nothing written.")
    return new


def main():
    with open(HTML_FILE, encoding="utf-8") as f:
        html = f.read()

    m = re.search(r"const YEARS = \[([^\]]+)\]", html)
    if not m:
        sys.exit("ERROR: YEARS array not found.")
    years = [int(y) for y in re.findall(r"\d{4}", m.group(1))]
    this_year = datetime.date.today().year
    if years[-1] >= this_year:
        sys.exit(f"ERROR: YEARS ends at {years[-1]}, which is not a complete "
                 f"calendar year. Annual averages would be partial.")
    print(f"Filling {len(years)} complete years: {years[0]}-{years[-1]}")

    latest = {}
    for name, series, url, freq, dp, div in SERIES:
        rows = fetch(url, series, freq)
        vals = annual(rows, years, dp, div)
        latest[name] = (rows[-1][0], rows[-1][1] / div)
        html = sub(html,
                   r"const " + name + r" = \[[^\]]*\];",
                   "const " + name + " = [" + ",".join(str(v) for v in vals) + "];",
                   name)
        print(f"  {name:10s} {years[-1]}={vals[-1]:<8} latest {rows[-1][0]} "
              f"= {rows[-1][1] / div:.3f}")

    as_of = latest["GAS_MA"][0]
    now = ("const FUEL_NOW = {asOf:'" + as_of + "', "
           f"gasMA:{latest['GAS_MA'][1]:.3f}, "
           f"gasUS:{latest['GAS_US'][1]:.3f}, "
           f"dieselNE:{latest['DIESEL_NE'][1]:.3f}}};")
    html = sub(html, r"const FUEL_NOW = \{[^}]*\};", now, "FUEL_NOW")
    print(f"  FUEL_NOW   as of {as_of}: MA gasoline ${latest['GAS_MA'][1]:.3f}/gal")

    # A current price that has silently become an annual average again is exactly
    # the bug this file was written to kill, so refuse to publish one.
    if abs(latest["GAS_MA"][1] - float(re.search(
            r"const GAS_MA = \[[^\]]*?([\d.]+)\];", html).group(1))) < 0.0001:
        print("  NOTE: current price equals the last annual average exactly -- "
              "check that FUEL_NOW is not being fed the wrong series.")

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  -> {os.path.basename(HTML_FILE)} written.")


if __name__ == "__main__":
    main()
