#!/usr/bin/env python3
"""update-tax-budget-dashboard.py — refresh the EIA electricity and BLS CPI figures
in tax-budget-dashboard.html.

Why this was rewritten
----------------------
The old version searched for the *value it had last written* as its anchor:

    html.replace("31.5¢", f"{ma_e:.1f}¢")

which made it single-shot. Its own first successful run removed the anchor, and every
run afterwards silently did nothing. By the time this was found, every literal it
targeted -- 31.5¢, 18.05¢, +75%, Nov 2025 -- was gone from the HTML entirely, so the
script could never fire again and never said so: it printed "No changes needed" and
exited 0. The GitHub Action went green every month while updating nothing.

Two of its replaces were also unguarded and global (`str.replace` with no count):

  * "+4.0%" appears in the CPI table's May-2024 historical row as well as in the
    current-shelter row, so a run would have silently rewritten recorded history.
  * "Nov 2025" would have rewritten any prose that happened to mention that month.

Every target is now located by *stable markup* -- a table row's label, a stat card's
heading, a Chart.js dataset label -- none of which change when the data does. The
current value is read out of the file rather than assumed. Each substitution is
anchored, bounded and applied exactly once. A missing anchor prints "!!" and leaves
the file untouched; this script never guesses and never writes blind.

This is the same repair applied to update-census-data.py -- read that one first if the
approach is unfamiliar.

Scope
-----
  EIA  → the Electricity stat card, the Live Cost Tracker's electricity row, the MA
         Cost Burden electricity row, and the chartElectricity bar array.
         The whole array is refreshed from one EIA call so every bar shares a vintage;
         if any state is missing the array is left alone rather than mixing months.
  BLS  → the Live Cost Tracker's All Items and Shelter rows (the widget that is
         explicitly labelled auto-updated). The "MA Cost Burden" table's rows carry
         their own printed vintage and are deliberately NOT touched.

Env:
  EIA_API_KEY  (free — www.eia.gov/opendata/register.php). Without it the EIA half is
               skipped loudly; the BLS half needs no key.
"""
import json, os, re, sys
from urllib.request import urlopen, Request
from datetime import datetime

EIA_KEY = os.environ.get("EIA_API_KEY", "").strip()
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tax-budget-dashboard.html")

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# chartElectricity's bars, in the order the chart draws them. The chart's own labels
# array is read at runtime and checked against this map, so a reordered chart fails
# loudly instead of silently mislabelling states.
CHART_STATES = [
    ("Massachusetts", "MA"), ("Connecticut", "CT"), ("Rhode Island", "RI"),
    ("New Hampshire", "NH"), ("New York", "NY"), ("US Average", "US"),
    ("Florida", "FL"), ("North Carolina", "NC"), ("Texas", "TX"),
]

failures = []


def fail(msg):
    """Record an anchor/fetch failure. Printed with !! so a CI log makes it obvious."""
    print(f"  !! {msg}")
    failures.append(msg)


# ── Fetchers ────────────────────────────────────────────────────────────────

def eia_fetch(state):
    """Latest monthly residential price for one state. Returns (cents_per_kwh, 'YYYY-MM')."""
    if not EIA_KEY:
        return None, None
    url = ("https://api.eia.gov/v2/electricity/retail-sales/data"
           f"?api_key={EIA_KEY}&frequency=monthly&data[0]=price"
           f"&facets[sectorid][]=RES&facets[stateid][]={state}"
           "&sort[0][column]=period&sort[0][direction]=desc&length=1")
    try:
        with urlopen(Request(url, headers={"User-Agent": "MA-Data-Hub/1.0"}), timeout=25) as r:
            row = json.loads(r.read())["response"]["data"][0]
        return float(row["price"]), row["period"]
    except Exception as e:
        fail(f"EIA fetch failed ({state}): {e}")
        return None, None


def bls_cpi(series_ids, start_yr, end_yr):
    url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    payload = json.dumps({"seriesid": series_ids,
                          "startyear": str(start_yr), "endyear": str(end_yr)}).encode()
    try:
        with urlopen(Request(url, data=payload,
                             headers={"Content-Type": "application/json",
                                      "User-Agent": "MA-Data-Hub/1.0"}), timeout=25) as r:
            data = json.loads(r.read())
        if data.get("status") != "REQUEST_SUCCEEDED":
            fail(f"BLS: {data.get('status')} {'; '.join(data.get('message', []))}")
            return {}
        return {s["seriesID"]: [(int(d["year"]), d["period"], float(d["value"]))
                                for d in s.get("data", [])]
                for s in data.get("Results", {}).get("series", [])}
    except Exception as e:
        fail(f"BLS fetch failed: {e}")
        return {}


def yoy(data):
    """Year-over-year % for the latest month present. Returns (pct, 'Mon YYYY')."""
    if not data or len(data) < 13:
        return None, None
    s = sorted(data, key=lambda x: (x[0], x[1]), reverse=True)
    latest = s[0]
    for d in s:
        if d[0] == latest[0] - 1 and d[1] == latest[1]:
            pct = round((latest[2] - d[2]) / d[2] * 100, 1)
            return pct, f"{MONTHS[int(latest[1].replace('M',''))]} {latest[0]}"
    return None, None


# ── Anchored substitution ───────────────────────────────────────────────────

def sub_once(html, pattern, build, what):
    """Rewrite the FIRST match of `pattern` using build(match) -> replacement.

    Anchored on markup, applied exactly once, never global. Returns (html, changed).
    A pattern that does not match is reported and changes nothing -- the old code
    would simply have moved on in silence.
    """
    m = re.search(pattern, html)
    if not m:
        fail(f"{what}: anchor not found -- NOT updated")
        return html, False
    new = build(m)
    if new == m.group(0):
        return html, False
    print(f"  {what}: updated")
    return html[:m.start()] + new + html[m.end():], True


def cents_row(html, label, ma, us, prem, period, what):
    """A table row: <strong>LABEL</strong></td><td..>XX.XX¢/kWh</td><td>YY.YY¢/kWh</td><td..>~ZZ%</td>..(EIA, Mon YYYY)"""
    pat = (r"(<strong>" + re.escape(label) + r"</strong></td><td[^>]*>)[\d.]+(¢/kWh</td><td[^>]*>)"
           r"[\d.]+(¢/kWh</td><td[^>]*>)~\d+(%</td><td[^>]*>EIA \()[^)]*(\))")
    return sub_once(html, pat,
                    lambda m: (f"{m.group(1)}{ma:.2f}{m.group(2)}{us:.2f}{m.group(3)}"
                               f"~{prem}{m.group(4)}{period}{m.group(5)}"),
                    what)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(HTML_FILE):
        print(f"ERROR: {HTML_FILE} not found.")
        sys.exit(1)
    print("=== Tax/Budget Dashboard Update ===\n")

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()
    orig = html

    # ── EIA electricity ──
    print("Fetching EIA (all chart states)...")
    if not EIA_KEY:
        fail("EIA_API_KEY not set -- skipping every electricity figure. "
             "Free key: www.eia.gov/opendata/register.php")
        rates, period = {}, None
    else:
        rates, periods = {}, set()
        for _name, sid in CHART_STATES:
            val, per = eia_fetch(sid)
            if val is not None:
                rates[sid], _ = val, periods.add(per)
                print(f"    {sid}: {val:.2f}¢  ({per})")
        # One vintage per chart. Mixing months across bars is exactly the error the
        # dashboard's own captions warn about, so refuse rather than mix.
        if len(periods) > 1:
            fail(f"EIA returned mixed periods {sorted(periods)} -- not updating the chart array")
            period = None
        else:
            period = periods.pop() if periods else None

    if rates.get("MA") and rates.get("US") and period:
        ma_e, us_e = rates["MA"], rates["US"]
        prem = round((ma_e - us_e) / us_e * 100)
        y, mo = period.split("-")
        el = f"{MONTHS[int(mo)]} {y}"

        # Stat card: <div class="label">Electricity Rate</div><div class="value red">X¢/kWh</div>
        # <div class="sub">vs Y¢ national avg (EIA, Mon YYYY)</div>
        html, _ = sub_once(
            html,
            r'(<div class="label">Electricity Rate</div><div class="value red">)[\d.]+'
            r'(¢/kWh</div><div class="sub">vs )[\d.]+(¢ national avg \(EIA, )[^)]*(\))',
            lambda m: f"{m.group(1)}{ma_e:.2f}{m.group(2)}{us_e:.2f}{m.group(3)}{el}{m.group(4)}",
            "Electricity stat card")

        html, _ = cents_row(html, "Electricity", ma_e, us_e, prem, el,
                            "Live Cost Tracker electricity row")

        # MA Cost Burden row: <td>Residential Electricity</td><td..>X¢/kWh</td>...
        html, _ = sub_once(
            html,
            r'(<td>Residential Electricity</td><td[^>]*>)[\d.]+(¢/kWh</td><td>)[\d.]+'
            r'(¢/kWh</td><td[^>]*>)~\d+(%</td><td>EIA Electric Power Monthly \()[^)]*(\))',
            lambda m: (f"{m.group(1)}{ma_e:.2f}{m.group(2)}{us_e:.2f}{m.group(3)}"
                       f"~{prem}{m.group(4)}{el}{m.group(5)}"),
            "MA Cost Burden electricity row")

        # chartElectricity array. Anchored on the dataset label, which does not move
        # when the data does. The bare numbers in here were unreachable to the old
        # script, which only ever matched "31.5¢" WITH the cent sign -- so the chart
        # silently kept a vintage the cards had long since left behind.
        lm = re.search(r"safeChart\('chartElectricity'.*?labels:\s*\[([^\]]*)\]", html, re.S)
        if not lm:
            fail("chartElectricity: labels array not found -- NOT updated")
        else:
            labels = [x.strip().strip("'\"") for x in lm.group(1).split(",")]
            expected = [n for n, _ in CHART_STATES]
            if labels != expected:
                fail(f"chartElectricity: labels {labels} != expected {expected} -- NOT updated")
            elif len(rates) != len(CHART_STATES):
                missing = [s for _n, s in CHART_STATES if s not in rates]
                fail(f"chartElectricity: no EIA data for {missing} -- array left at its "
                     "published vintage rather than mixing months")
            else:
                vals = ",".join(f"{rates[s]:.2f}" for _n, s in CHART_STATES)
                html, _ = sub_once(
                    html,
                    r"(label: '¢ per kWh', data: \[)[^\]]*(\])",
                    lambda m: f"{m.group(1)}{vals}{m.group(2)}",
                    "chartElectricity array")
                # The chart's own title and source carry the month; move them with it.
                html, _ = sub_once(
                    html,
                    r"(<h3>EIA Residential Electricity Rates — MA vs Selected States \(¢/kWh, )[^)]*(\)</h3>)",
                    lambda m: f"{m.group(1)}{el}{m.group(2)}", "chartElectricity title")
                html, _ = sub_once(
                    html,
                    r"(Source: U\.S\. Energy Information Administration, Electric Power Monthly \()[^)]*(\))",
                    lambda m: f"{m.group(1)}{el}{m.group(2)}", "chartElectricity source")

    # ── BLS CPI: the Live Cost Tracker rows only ──
    print("\nFetching BLS CPI...")
    now = datetime.now()
    cpi = bls_cpi(["CUSR0000SA0", "CUSR0100SA0", "CUSR0000SAH1", "CUSR0100SAH1"],
                  now.year - 1, now.year)
    us_cpi, us_lbl = yoy(cpi.get("CUSR0000SA0", []))
    ne_cpi, ne_lbl = yoy(cpi.get("CUSR0100SA0", []))
    us_sh, _ = yoy(cpi.get("CUSR0000SAH1", []))
    ne_sh, _ = yoy(cpi.get("CUSR0100SAH1", []))
    print(f"  US CPI:{us_cpi}% NE CPI:{ne_cpi}% US Shelter:{us_sh}% NE Shelter:{ne_sh}%")

    def tracker_row(html, label, ne_val, us_val, ne_month, what):
        """Live Cost Tracker row: label, Boston/NE %, US %, the pp gap, and the vintage.

        The gap column is recomputed here rather than left as whatever it was when the
        row was last hand-typed -- that is how "+27.5% vs +26.2%" style mismatches get
        in. Sign and CSS class follow the recomputed value.
        """
        if ne_val is None or us_val is None:
            return html, False
        gap = round(ne_val - us_val, 1)
        cls = "highlight" if gap >= 0 else "good"
        pat = (r"(<tr><td><strong>" + re.escape(label) + r"</strong></td><td[^>]*>)"
               r"\+?[\d.-]+(%</td><td[^>]*>)\+?[\d.-]+(%</td><td class=\")[^\"]*(\">)"
               r"[+-]?[\d.]+(pp</td><td>BLS CPI \()[^)]*(\)</td></tr>)")
        return sub_once(html, pat,
                        lambda m: (f"{m.group(1)}{ne_val:+.1f}{m.group(2)}{us_val:+.1f}"
                                   f"{m.group(3)}{cls}{m.group(4)}{gap:+.1f}"
                                   f"{m.group(5)}{ne_month}{m.group(6)}"),
                        what)

    if ne_lbl:
        html, _ = tracker_row(html, "All Items (CPI-U)", ne_cpi, us_cpi, ne_lbl,
                              "Live Cost Tracker: All Items")
        html, _ = tracker_row(html, "Shelter / Housing", ne_sh, us_sh, ne_lbl,
                              "Live Cost Tracker: Shelter")

    # ── Write ──
    if html != orig:
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\nDone — updated {HTML_FILE}")
    else:
        print("\nNo changes needed.")

    # A dead anchor must not look like a clean run. The old script's whole failure mode
    # was exiting 0 while doing nothing, for months, unnoticed.
    if failures:
        print(f"\n{len(failures)} problem(s) above -- some figures were NOT updated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
