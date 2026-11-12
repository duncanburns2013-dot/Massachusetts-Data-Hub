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
  Feeds (no network) → data/cost-of-living-latest.json: the RPP data-fields, the
         RPP_MA / RPP_MA_RENT constants, and the chartRPPTime, chartRPP,
         chartPurchasing and chartIncomeReal arrays (ACS 1-year median household
         income, every state from one release). data/property-levy-latest.json
         (refreshed by hand from the DLS Databank, which blocks scripts): chartLevy
         and the levy stat card and Prop 2½ prose.
  EIA  →the Electricity stat card, the Live Cost Tracker's electricity row, the MA
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
import json, os, re, sys, time
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
    # Retried, because a single EIA wobble used to take the whole script down and
    # with it the work of every step before this one. On 2026-10-20 MA and RI both
    # read-timed-out, this returned None for them, the partial-figure guard
    # correctly refused to publish, the script exited non-zero -- and the
    # workflow's commit step was then SKIPPED, discarding a successful energy
    # dashboard write from four steps earlier. Two transient timeouts out of nine
    # requests threw away the whole run.
    #
    # 3 tries x 25s + 8s of backoff, over 9 states, is about 12 minutes worst
    # case, inside this job's 30-minute ceiling. Same reasoning as get() in
    # update-cost-of-living.py, which was given retries after all 50 of its state
    # requests timed out on 2026-08-22.
    last = None
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "MA-Data-Hub/1.0"}),
                         timeout=25) as r:
                row = json.loads(r.read())["response"]["data"][0]
            return float(row["price"]), row["period"]
        except Exception as e:
            last = e
            if attempt < 2:
                time.sleep(4 * (attempt + 1))
    fail(f"EIA fetch failed ({state}) after 3 tries: {last}")
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
        # BLS returns "-" (and occasionally "") for a month it never published --
        # October 2025 is one, lost to the shutdown. float("-") raises, which took the
        # whole run down and, because the chart writes happen earlier, discarded work
        # that had already succeeded. Skip non-numeric observations instead: a missing
        # month is normal data, not a failure.
        def _obs(series):
            out = []
            for d in series.get("data", []):
                try:
                    out.append((int(d["year"]), d["period"], float(d["value"])))
                except (ValueError, TypeError, KeyError):
                    print(f"  note: {series.get('seriesID','?')} "
                          f"{d.get('year','?')}-{d.get('period','?')} "
                          f"not published ({d.get('value','?')!r}) -- skipped")
            return out
        return {s["seriesID"]: _obs(s)
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


def set_field_all(html, tag, value, what):
    """Write EVERY occurrence of one data-field. Returns (html, changed).

    sub_once deliberately rewrites only the first match, which is right for a
    stamp that appears once. These fields do not: rpp-ma is printed four times
    on this page -- hero strip, stat card, the sentence explaining how to read
    the index, and the cost-burden table -- and the whole reason they were wrong
    is that each copy was maintained by hand and none agreed with the feed. A
    field that exists in several places has to be written in all of them or the
    page contradicts itself, which is worse than being uniformly stale.
    """
    pat = r'(data-field="' + re.escape(tag) + r'">)[^<]*(<)'
    n = len(re.findall(pat, html))
    if n == 0:
        fail(f"{what}: data-field=\"{tag}\" not found -- NOT updated")
        return html, False
    new = re.sub(pat, lambda m: m.group(1) + value + m.group(2), html)
    if new == html:
        return html, False
    print(f"  {what}: {value} ({n} place{'s' if n > 1 else ''})")
    return new, True


def rpp_fields(html):
    """Massachusetts' BEA Regional Price Parity, from the feed that owns it.

    These four figures -- the index, the premium over 100, what $100 is worth,
    and the vintage year -- were hand-typed in nine places between them. BEA
    publishes RPP once a year, so they were right when written and then simply
    sat there: the index is the single most quoted number on this page and
    nothing could move it.

    The source of truth is data/cost-of-living-latest.json, written by
    update-cost-of-living.py from the BEA regional zips. Reading the feed rather
    than re-fetching BEA keeps one fetch behind one figure and means this page
    cannot disagree with the affordability dashboard about the same index.
    """
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "data", "cost-of-living-latest.json")
    if not os.path.exists(f):
        fail("data/cost-of-living-latest.json missing -- RPP figures NOT updated")
        return html
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    try:
        rpp = float(d["rpp"]["MA"]["all"])
        year = str(d["meta"]["rpp_year"])
    except (KeyError, TypeError, ValueError) as e:
        fail(f"cost-of-living feed shape unexpected ({e}) -- RPP figures NOT updated")
        return html
    # An index at or below 100 would invert every claim built on it, so it is a
    # refusal and not a rounding question.
    if not 80 < rpp < 150:
        fail(f"RPP {rpp} outside 80-150 -- refusing to publish it")
        return html

    print("")
    print(f"BEA RPP (MA, {year}): {rpp}")
    for tag, val, what in (
            ("rpp-ma",    f"{rpp:.1f}",            "RPP index"),
            ("rpp-prem",  f"{rpp - 100:.1f}%",     "RPP premium over US"),
            ("rpp-buys",  f"${100 / (rpp / 100):.2f}", "what $100 buys"),
            ("rpp-year",  year,                    "RPP vintage")):
        html, _ = set_field_all(html, tag, val, what)
    return html


# ── Charts written from data/*.json ─────────────────────────────────────────
#
# chartRPPTime, chartRPP, chartPurchasing, chartIncomeReal and chartLevy were all
# hand-typed arrays. Found 2026-11-08: the MA RPP history was off by 2-4 points for
# 2008-2019 and stopped a year short; the state RPP bars and the $100-buys bars
# were an older vintage than the MA figure beside them; the income bars were a CPS
# figure that matched no published year; and the levy series ran $0.3-0.5B low
# for FY2016-FY2023. Each is now rewritten from the feed that owns it, anchored on
# its dataset label, inside its own safeChart(...) block.

CHART_ABBR = {
    "Massachusetts": "MA", "New Jersey": "NJ", "California": "CA", "New York": "NY",
    "New Hampshire": "NH", "NH": "NH", "Florida": "FL", "North Carolina": "NC",
    "Texas": "TX", "Tennessee": "TN",
}


def chart_block(html, cid):
    """(start, end) of the safeChart('cid', ...) call, up to the next chart or break."""
    m = re.search(r"safeChart\('" + re.escape(cid) + r"'", html)
    if not m:
        return None
    nxt = re.search(r"safeChart\(|\bbreak;", html[m.end():])
    return m.start(), m.end() + (nxt.start() if nxt else len(html) - m.end())


def chart_labels(html, cid):
    span = chart_block(html, cid)
    if not span:
        fail(f"{cid}: chart not found -- NOT updated")
        return None
    lm = re.search(r"labels:\s*\[([^\]]*)\]", html[span[0]:span[1]])
    if not lm:
        fail(f"{cid}: labels array not found -- NOT updated")
        return None
    return [x.strip().strip("'\"") for x in lm.group(1).split(",")]


def set_chart_array(html, cid, pattern, values, what):
    """Rewrite one array inside one chart's block. pattern has groups (prefix)(suffix)."""
    span = chart_block(html, cid)
    if not span:
        fail(f"{what}: chart {cid} not found -- NOT updated")
        return html
    block = html[span[0]:span[1]]
    block, _ = sub_once(block, pattern, lambda m: m.group(1) + values + m.group(2), what)
    return html[:span[0]] + block + html[span[1]:]


def state_values(html, cid, table, what, us=None):
    """Map a chart's state labels onto a {ST: value} table; None if any is missing."""
    labels = chart_labels(html, cid)
    if labels is None:
        return None
    out = []
    for lab in labels:
        if lab == "US Average" and us is not None:
            out.append(us)
        elif CHART_ABBR.get(lab) in table:
            out.append(float(table[CHART_ABBR[lab]]))
        else:
            fail(f"{what}: no value for chart label '{lab}' -- array left untouched")
            return None
    return out


def feed_charts(html):
    """RPP and median-income charts, from data/cost-of-living-latest.json."""
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "data", "cost-of-living-latest.json")
    try:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        rpp = {st: v["all"] for st, v in d["rpp"].items()}
        years, hist = d["years"], d["ma_history"]["all"]
        rpp_year = str(d["meta"]["rpp_year"])
        inc = d["income"]
    except (OSError, KeyError, TypeError, ValueError) as e:
        fail(f"cost-of-living feed unreadable ({e}) -- RPP/income charts NOT updated")
        return html
    print("\nCharts from data/cost-of-living-latest.json")

    # The CPI tab's RPP callouts compute from two JS constants. Same feed, same
    # vintage as the cards, so the two tabs cannot quote different indices.
    html, _ = sub_once(html, r"(var RPP_MA=)[\d.]+(;)",
                       lambda m: f"{m.group(1)}{rpp['MA']}{m.group(2)}", "RPP_MA constant")
    html, _ = sub_once(html, r"(var RPP_MA_RENT=)[\d.]+(;)",
                       lambda m: f"{m.group(1)}{d['rpp']['MA']['housing']}{m.group(2)}",
                       "RPP_MA_RENT constant")

    # MA RPP over time. The series must end on the same year the cards quote.
    if len(years) != len(hist) or str(years[-1]) != rpp_year:
        fail(f"chartRPPTime: years/history mismatch ({len(years)}/{len(hist)}, "
             f"last {years[-1]} vs rpp_year {rpp_year}) -- NOT updated")
    else:
        html = set_chart_array(html, "chartRPPTime", r"(labels:\s*\[)[^\]]*(\])",
                               ",".join(f"'{y}'" for y in years), "chartRPPTime labels")
        html = set_chart_array(html, "chartRPPTime",
                               r"(label: 'MA RPP \(All Items\)', data: \[)[^\]]*(\])",
                               ",".join(f"{v:.1f}" for v in hist), "chartRPPTime MA series")
        html = set_chart_array(html, "chartRPPTime",
                               r"(label: 'US Average \(100\)', data: \[)[^\]]*(\])",
                               ",".join("100" for _ in years), "chartRPPTime US baseline")
        html, _ = set_field_all(html, "rpp-span", f"{years[0]}–{years[-1]}", "RPP history span")

    # State RPP bars and what $100 buys, one vintage for every bar.
    vals = state_values(html, "chartRPP", rpp, "chartRPP", us=100.0)
    if vals:
        html = set_chart_array(html, "chartRPP",
                               r"(label: 'Regional Price Parity \(US=100\)', data: \[)[^\]]*(\])",
                               ",".join(f"{v:.1f}" for v in vals), "chartRPP array")
    vals = state_values(html, "chartPurchasing", rpp, "chartPurchasing", us=100.0)
    if vals:
        html = set_chart_array(html, "chartPurchasing",
                               r"(label: 'Real Value of \$100', data: \[)[^\]]*(\])",
                               ",".join(f"{10000 / v:.2f}" for v in vals), "chartPurchasing array")

    # Median household income, nominal and RPP-adjusted. ACS 1-year B19013, every
    # state from one release; the CPS figure in the cost-burden table is a
    # different survey and is labelled as such there.
    by_state = inc.get("household_by_state") or {}
    if not by_state or not str(inc.get("source", "")).startswith("Census ACS 1-Year"):
        fail("income.household_by_state missing from the feed -- chartIncomeReal NOT updated")
    else:
        nom = state_values(html, "chartIncomeReal", by_state, "chartIncomeReal")
        labels = chart_labels(html, "chartIncomeReal")
        if nom and labels:
            real = [n * 100 / rpp[CHART_ABBR[l]] for n, l in zip(nom, labels)]
            html = set_chart_array(html, "chartIncomeReal",
                                   r"(label: 'Nominal Median HH Income', data: \[)[^\]]*(\])",
                                   ",".join(f"{v:.0f}" for v in nom), "chartIncomeReal nominal")
            html = set_chart_array(html, "chartIncomeReal",
                                   r"(label: 'RPP-Adjusted \(Real\)', data: \[)[^\]]*(\])",
                                   ",".join(f"{v:.0f}" for v in real), "chartIncomeReal real")
            html, _ = set_field_all(html, "acs-hh-year", str(inc["vintage"]), "ACS income vintage")
    return html


def levy_fields(html):
    """Statewide property-tax levy, from data/property-levy-latest.json.

    That file is refreshed by hand from the DLS Municipal Databank, which refuses
    scripted requests. This writes the chart, the stat card and the Prop 2½ prose
    from it, so a refresh of the file is the only edit a new fiscal year needs.
    """
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "data", "property-levy-latest.json")
    try:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        series = d["statewide_total_levy"]
        verified = d["meta"]["verified"]
    except (OSError, KeyError, TypeError, ValueError) as e:
        fail(f"levy feed unreadable ({e}) -- levy chart and figures NOT updated")
        return html
    # Chart from FY2015 on, the year the Prop 2½ paragraph measures from.
    fys = sorted(k for k in series if int(k[2:]) >= 2015)
    vals = [series[k] / 1e9 for k in fys]
    if any(b <= a for a, b in zip(vals, vals[1:])) or not 5 < vals[-1] < 60:
        fail(f"levy series fails sanity check {vals} -- NOT updated")
        return html
    print(f"\nStatewide levy ({fys[0]}-{fys[-1]}): ${vals[0]:.2f}B -> ${vals[-1]:.2f}B")
    html = set_chart_array(html, "chartLevy", r"(labels:\s*\[)[^\]]*(\])",
                           ",".join(f"'FY{k[4:]}'" for k in fys), "chartLevy labels")
    html = set_chart_array(html, "chartLevy", r"(label: 'Total Levy \(\$B\)', data: \[)[^\]]*(\])",
                           ",".join(f"{v:.2f}" for v in vals), "chartLevy array")
    y, mo, dd = verified.split("-")
    for tag, val, what in (
            ("levy-latest",   f"${vals[-1]:.1f}B",                      "levy, latest FY"),
            ("levy-fy",       fys[-1],                                  "levy, latest FY label"),
            ("levy-yoy",      f"${vals[-1] - vals[-2]:.1f}B",            "levy, change on the year"),
            ("levy-first",    f"${vals[0]:.1f}B",                       "levy, first FY"),
            ("levy-first-fy", fys[0],                                   "levy, first FY label"),
            ("levy-growth",   f"{round((vals[-1] / vals[0] - 1) * 100)}%", "levy growth"),
            ("levy-verified", f"{int(dd)} {MONTHS[int(mo)]} {y}",       "levy read date")):
        html, _ = set_field_all(html, tag, val, what)
    return html


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

    # ── BEA Regional Price Parity, from the cost-of-living feed ──
    html = rpp_fields(html)
    html = feed_charts(html)
    html = levy_fields(html)

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

    # ── Stamp the page with the vintage of its own data ──
    # Unconditional, like the CBP page's stamp and for the same reason: if it
    # only fired when a number moved, a feed that quietly stopped returning new
    # months would leave an old date looking current -- which is this script's
    # documented failure mode, going green while updating nothing.
    #
    # The page carries two vintages, EIA electricity and BLS CPI, and they can
    # sit a month apart. The OLDER of the two is stamped, so the page never
    # claims to be fresher than its stalest figure.
    #
    # Written into anchors, never by searching for the month as text. Elsewhere
    # the page says a Census release "has not been published as of July 2026" --
    # prose about something that has NOT happened. A global month replace would
    # march that sentence forward every run and make it a false statement, which
    # is the trap this file's docstring flags at the top.
    # Boston/NE CPI is published every other month, so ne_lbl is absent about half
    # the time. Taking the BLS vintage from whichever of the two series answered
    # keeps the stamp working in those months; reading ne_lbl alone left the page
    # unstamped on every off-month, which is the silence this is meant to end.
    vintages, sources = [], []
    if period:                                   # EIA, 'YYYY-MM'
        vintages.append(period)
        sources.append(f"EIA {period}")
    for name, lbl in (("BLS Boston/NE", ne_lbl), ("BLS US", us_lbl)):
        if lbl:                                  # BLS, 'Mon YYYY'
            mon, yr = lbl.split()
            vintages.append("%s-%02d" % (yr, MONTHS.index(mon)))
            sources.append(f"{name} {lbl}")
            break
    if vintages:
        oldest = min(vintages)                   # ISO sorts chronologically
        y, mo = oldest.split("-")
        pretty = f"{MONTHS[int(mo)]} {y}"
        html, ok1 = sub_once(
            html, r'(<meta name="data-checked" content=")[^"]*(">)',
            lambda m: f"{m.group(1)}{oldest}-01{m.group(2)}", "data-checked stamp")
        html, ok2 = sub_once(
            html, r'(<span data-field="page-updated">)[^<]*(</span>)',
            lambda m: f"{m.group(1)}{pretty}{m.group(2)}", "page-updated stamp")
        if ok1 or ok2:
            print(f"\nStamped page vintage -> {pretty} "
                  f"(oldest of: {', '.join(sources)}).")
    else:
        fail("no EIA or BLS vintage available -- page date NOT stamped")

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
