#!/usr/bin/env python3
"""update-energy-dashboard.py — refresh EIA electricity data in energy-dashboard.html.

Pulls live data from the EIA Electric Power Monthly API and rewrites the figures
listed in `subs` below — NOT, despite what this docstring used to claim, "every
electricity-rate figure on the dashboard". It writes:

  * Latest monthly residential rates (hero stats, overview cards, the New England
    rate table, the overview bar chart, and the rate figures woven into the
    H.5151 / Boston / lifecycle prose).
  * The 2010-2025 annual history series (ELEC_MA / ELEC_US) and the closed-year
    annual-average comparison card.

Everything else on the page is either derived in-browser from the rate table this
script writes (see the "Derived figures" block in the HTML — that is the
preferred home for any new figure) or is a deliberately frozen vintage.

Why this script looks different from a naive find-and-replace:

  Every substitution below is *value-agnostic* — the regex matches whatever
  number is on the page right now (e.g. `[\\d.]+`), not a hard-coded previous
  value. That makes the script idempotent and, crucially, self-renewing: it can
  never silently freeze the way a literal "31.16" -> "30.46" swap does once the
  old literal is gone.

  If any anchor is missing (the surrounding HTML changed), the script exits
  non-zero so the GitHub Action FAILS LOUDLY instead of committing nothing and
  looking healthy.

  That anchor check only ever caught the *loud* failure mode. The quiet one --
  a figure with no anchor at all, which no pattern claims and nothing checks --
  is what actually rotted the page: the S.3143 card sat at 30.21c/$819 and two
  charts plotted $765's predecessor $922 for months while every anchored figure
  moved on. The staleness guard at the bottom closes that hole: after
  substitution it re-reads the file and fails if any live region still carries a
  rate or per-year figure this run did not produce.

Requires the EIA_API_KEY environment variable (set as a repo secret).
"""
import json
import os
import re
import ssl
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError

API_KEY = os.environ.get("EIA_API_KEY", "").strip()
if not API_KEY:
    sys.exit("ERROR: set the EIA_API_KEY environment variable.")

HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "energy-dashboard.html")
EIA_BASE = "https://api.eia.gov/v2/electricity/retail-sales/data/"

MON_ABBR = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MON_FULL = ["", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"]

# States shown in the New England table and the overview bar chart.
STATES = ["MA", "US", "RI", "CT", "NY", "FL", "TX"]

KWH_PER_MONTH = 600          # billing assumption used across the dashboard
KWH_PER_YEAR = KWH_PER_MONTH * 12


# --------------------------------------------------------------------------
# EIA API
# --------------------------------------------------------------------------
def _fetch(params):
    """GET the EIA API and return the `response.data` list."""
    url = EIA_BASE + "?api_key=" + API_KEY + "".join(
        f"&{k}={v}" for k, v in params)
    req = Request(url, headers={"User-Agent": "ma-data-hub-energy"})
    try:
        with urlopen(req, timeout=30) as r:
            payload = json.loads(r.read())
    except URLError as e:
        # Some runners ship a broken trust store (urlopen wraps the
        # SSLCertVerificationError in a URLError). EIA data is public and the
        # API key already travels in the URL, so an unverified retry leaks
        # nothing extra — but warn so it is never silently relied upon.
        if not isinstance(e.reason, ssl.SSLError):
            raise
        print("WARN: TLS verification failed; retrying without verification.",
              file=sys.stderr)
        with urlopen(req, timeout=30,
                     context=ssl._create_unverified_context()) as r:
            payload = json.loads(r.read())
    return payload["response"]["data"]


def latest_monthly(state):
    """Return (price float, 'YYYY-MM') for the most recent residential month."""
    rows = _fetch([
        ("frequency", "monthly"), ("data[0]", "price"),
        ("facets[sectorid][]", "RES"), ("facets[stateid][]", state),
        ("sort[0][column]", "period"), ("sort[0][direction]", "desc"),
        ("length", "1"),
    ])
    if not rows:
        sys.exit(f"ERROR: EIA returned no monthly data for {state}.")
    return float(rows[0]["price"]), rows[0]["period"]


def annual_series(state, start, end):
    """Return ([price floats ascending], latest_year_str) for RES rates."""
    rows = _fetch([
        ("frequency", "annual"), ("data[0]", "price"),
        ("facets[sectorid][]", "RES"), ("facets[stateid][]", state),
        ("start", str(start)), ("end", str(end)),
        ("sort[0][column]", "period"), ("sort[0][direction]", "asc"),
        ("length", "100"),
    ])
    return [round(float(r["price"]), 2) for r in rows], rows[-1]["period"]


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------
def cents(v):
    """Rate display: always two decimals, e.g. 30.21, 17.30."""
    return f"{v:.2f}"


def dollars(v):
    """Whole-dollar display with thousands separators, e.g. 2,175."""
    return f"{round(v):,}"


def premium_pct(rate, us):
    """Whole-percent premium of `rate` over the US average."""
    return round((rate - us) / us * 100)


# --------------------------------------------------------------------------
# Fetch everything
# --------------------------------------------------------------------------
print("Fetching EIA residential electricity rates...")
rate = {}
period = None
for st in STATES:
    price, per = latest_monthly(st)
    rate[st] = price
    if st == "MA":
        period = per
    print(f"  {st}: {price}c/kWh ({per})")

year, month = (int(x) for x in period.split("-"))
mon_abbr = f"{MON_ABBR[month]} {year}"
mon_full = f"{MON_FULL[month]} {year}"

ma, us = rate["MA"], rate["US"]
prem = premium_pct(ma, us)
overpay = round((ma - us) / 100 * KWH_PER_YEAR)
print(f"\nLatest month {mon_abbr}: MA {ma}c  US {us}c  +{prem}%  ${overpay}/yr")

# Annual history series — year range is taken from the YEARS array already in
# the HTML so the rebuilt arrays always match its length.
with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()

years_match = re.search(r"const YEARS = \[([^\]]+)\]", html)
if not years_match:
    sys.exit("ERROR: could not find the YEARS array in the HTML.")
years = re.findall(r"\d{4}", years_match.group(1))
y_start, y_end = int(years[0]), int(years[-1])

elec_ma, _ = annual_series("MA", y_start, y_end)
elec_us, ann_year = annual_series("US", y_start, y_end)
ann_ma, ann_us = elec_ma[-1], elec_us[-1]
ann_prem = premium_pct(ann_ma, ann_us)
print(f"Annual {ann_year} avg: MA {ann_ma}c  US {ann_us}c  +{ann_prem}%")

if len(elec_ma) != len(years) or len(elec_us) != len(years):
    sys.exit(f"ERROR: EIA annual series ({len(elec_ma)} pts) does not match "
             f"the {len(years)}-year YEARS array.")


# --------------------------------------------------------------------------
# Build the New England rate table + overview bar chart
# --------------------------------------------------------------------------
def table_row(name, st, highlight=False, good=False):
    cls = ' class="highlight"' if highlight else (' class="good"' if good else "")
    r = rate[st]
    annual = r / 100 * KWH_PER_YEAR
    if st == "US":
        vs_nat, extra = "&#x2014;", "&#x2014;"
    else:
        p = premium_pct(r, us)
        vs_nat = f"{p:+d}%"
        diff = round((r - us) / 100 * KWH_PER_YEAR)
        extra = f"+${diff:,}" if diff >= 0 else f"-${abs(diff):,}"
    td = lambda v: f'<td{cls}>{v}</td>' if (highlight or good) else f'<td>{v}</td>'
    name_td = (f'<td class="highlight">{name}</td>' if highlight
               else f'<td>{name}</td>')
    # vs-National and Annual-Cost cells inherit the row tint only when present.
    cell = (lambda v: f'<td class="highlight">{v}</td>') if highlight else (
        lambda v: f'<td>{v}</td>')
    return (f'<tr>{name_td}{td(cents(r))}{cell(vs_nat)}'
            f'{td("$" + dollars(annual))}{cell(extra)}</tr>')


table_rows = "\n".join([
    table_row("Massachusetts", "MA", highlight=True),
    table_row("Rhode Island", "RI"),
    table_row("Connecticut", "CT"),
    table_row("New York", "NY"),
    table_row("US Average", "US", good=True),
    table_row("Florida", "FL", good=True),
    table_row("Texas", "TX", good=True),
])

# Overview bar chart order: MA, CT, NY, RI, US Avg, TX, FL
bar_data = ",".join(str(rate[s]) for s in ["MA", "CT", "NY", "RI", "US", "TX", "FL"])

elec_ma_js = ",".join(str(v) for v in elec_ma)
elec_us_js = ",".join(str(v) for v in elec_us)


# --------------------------------------------------------------------------
# Substitutions — every pattern matches the CURRENT value, not a fixed literal.
# --------------------------------------------------------------------------
S, F, D = re.S, 0, re.S  # flag aliases for readability

subs = [
    # (label, pattern, replacement, flags)
    ("hero strip — MA rate",
     r'(<div class="val bad">)[\d.]+(&#x00A2;</div><div class="lbl">Per kWh \(EIA )[A-Za-z]+ \d{4}(\))',
     rf'\g<1>{cents(ma)}\g<2>{mon_abbr}\g<3>', F),

    ("hero strip — premium",
     r'(<div class="val bad">\+)\d+(%</div><div class="lbl">Above National Avg)',
     rf'\g<1>{prem}\g<2>', F),

    ("overview alert — MA/US/period",
     r'(MA residential rate: <strong>)[\d.]+(&#x00A2;/kWh</strong> &#x2014; national average: )[\d.]+(&#x00A2; \(EIA )[A-Za-z]+ \d{4}(\))',
     rf'\g<1>{cents(ma)}\g<2>{cents(us)}\g<3>{mon_abbr}\g<4>', F),

    ("overview card — MA rate",
     r'(MA Residential Rate</div><div class="value red">)[\d.]+(&#x00A2;</div><div class="sub">Per kWh \(EIA )[A-Za-z]+ \d{4}',
     rf'\g<1>{cents(ma)}\g<2>{mon_abbr}', F),

    ("overview card — US rate",
     r'(National Average</div><div class="value green">)[\d.]+(&#x00A2;)',
     rf'\g<1>{cents(us)}\g<2>', F),

    ("overview card — overpayment",
     r'(Annual Overpayment</div><div class="value red">\$)[\d,]+',
     rf'\g<1>{dollars(overpay)}', F),

    ("overview card — FL rate",
     r'(FL Rate</div><div class="value green">)[\d.]+(&#x00A2;)',
     rf'\g<1>{cents(rate["FL"])}\g<2>', F),

    ("annual-average card",
     r'(<div class="label">)\d{4}( Annual Avg Premium</div><div class="value red">\+)\d+(%</div><div class="sub">)[\d.]+(&#x00A2; MA vs )[\d.]+(&#x00A2; US &#x2014; full-year EIA)',
     rf'\g<1>{ann_year}\g<2>{ann_prem}\g<3>{cents(ann_ma)}\g<4>{cents(ann_us)}\g<5>', F),

    # The `</div>` anchor keeps this off the sector table's source line
    # (line ~259), which carries an intentionally older "October 2025" vintage.
    ("overview bar-chart source",
     r'(EIA Electric Power Monthly Table 5\.6\.A, )[A-Za-z]+ \d{4}(</div>)',
     rf'\g<1>{mon_full}\g<2>', F),

    ("New England table — header period",
     r'(All Among the Highest \(EIA )[A-Za-z]+ \d{4}(\))',
     rf'\g<1>{mon_abbr}\g<2>', F),

    ("New England table — rows",
     r'(New England Electricity Rates.*?<tbody>)(.*?)(</tbody>)',
     rf'\g<1>\n{table_rows}\n\g<3>', S),

    ("New England table — source period",
     r'(EIA Electric Power Monthly, Table 5\.6\.A, )[A-Za-z]+ \d{4}',
     rf'\g<1>{mon_full}', F),

    ("sector-table note — period + MA rate",
     r'(Residential rate updated to )[A-Za-z]+ \d{4} \([\d.]+(&#x00A2;\) in hero stats)',
     rf'\g<1>{mon_abbr} ({cents(ma)}\g<2>', F),

    ("H.5151 chart source — period",
     r'(Source: EIA )[A-Za-z]+ \d{4}(, bill text analysis)',
     rf'\g<1>{mon_abbr}\g<2>', F),

    ("H.5151 card — overpayment + MA/US",
     r'(Annual MA Overpayment</div><div class="value red">\$)[\d,]+(</div><div class="sub">)[\d.]+(&#x00A2; vs )[\d.]+(&#x00A2; &#x00D7; 600 kWh/mo)',
     rf'\g<1>{dollars(overpay)}\g<2>{cents(ma)}\g<3>{cents(us)}\g<4>', F),

    # The rank that used to sit here ("Still #2 most expensive") is now derived
    # in-page from this table's own rows -- see the "Derived figures" block in
    # the HTML. Only the dollar figure is written from here.
    ("H.5151 gap-closed card",
     r'(\$150 of \$)[\d,]+(\. <span id="gapClosedRank">)',
     rf'\g<1>{dollars(overpay)}\g<2>', F),

    ("H.5151 state-comparison source",
     r'(Source: EIA )[A-Za-z]+ \d{4}( rates &#x00D7;)',
     rf'\g<1>{mon_abbr}\g<2>', F),

    ("lifecycle — YOUR BILL rate + overpayment",
     r'(<div class="lc-name">)[\d.]+(&#x00A2;/kWh &#x2014; <span id="lcRank">.*?</span></div>'
     r'<div class="lc-year">\$)[\d,]+(/yr above national avg)',
     rf'\g<1>{cents(ma)}\g<2>{dollars(overpay)}\g<3>', F),

    ("lifecycle source — period",
     r'(Acts of the Legislature; EIA )[A-Za-z]+ \d{4}',
     rf'\g<1>{mon_abbr}', F),

    # NOTE: the "Equivalence" tab is a separate hand-built model — its
    # per-gallon figures ($1.97/gal), progress-bar widths and the $6.83
    # headline are all derived from the overpayment. Updating one number
    # there without recomputing the rest would make it *less* consistent,
    # so this script deliberately leaves that tab alone.

    ("Boston alert — mandate premium",
     r'(The \$)[\d,]+(/yr mandate premium is untouched)',
     rf'\g<1>{dollars(overpay)}\g<2>', F),

    ("Boston card — mandate premium",
     r'(<div class="value red">\$)[\d,]+(/yr</div><div class="sub">What policy actually costs)',
     rf'\g<1>{dollars(overpay)}\g<2>', F),

    ("Boston chart source — overpayment",
     r'(EIA rate data \(\$)[\d,]+(/yr overpayment)',
     rf'\g<1>{dollars(overpay)}\g<2>', F),

    ("Boston info-box — mandate premium",
     r'(while paying \$)[\d,]+( in mandate premiums)',
     rf'\g<1>{dollars(overpay)}\g<2>', F),

    ("Boston vs-item — grid rate",
     r'(on a grid already at )[\d.]+(&#x00A2;/kWh)',
     rf'\g<1>{cents(ma)}\g<2>', F),

    ("Boston total — mandate premium",
     r'(<div class="tn" style="color:var\(--red\)">\$)[\d,]+(/yr</div><div class="tl">Mandate Premium)',
     rf'\g<1>{dollars(overpay)}\g<2>', F),

    ("Boston expose — gas decommission rate",
     r'(onto the electric grid &#x2014; at )[\d.]+(&#x00A2;/kWh)',
     rf'\g<1>{cents(ma)}\g<2>', F),

    ("Boston chain — RATES HIT + premium",
     r'(RATES HIT )[\d.]+(&#x00A2;</div><div class="sd"><span id="chainRank">.*?</span>\. \+)\d+(% above national avg)',
     rf'\g<1>{cents(ma)}\g<2>{prem}\g<3>', F),

    ("Boston chain — BCCE problem",
     r'(BCCE saves \$200/yr on a \$)[\d,]+(/yr problem)',
     rf'\g<1>{dollars(overpay)}\g<2>', F),

    ("Boston verdict — rate + problem",
     r'(They drove rates to )[\d.]+(&#x00A2;\. Now they offer you \$200/yr on a \$)[\d,]+(/yr problem)',
     rf'\g<1>{cents(ma)}\g<2>{dollars(overpay)}\g<3>', F),

    ("overview bar-chart data",
     r"(chartRatesOverview',\{type:'bar',data:\{labels:\['MA','CT','NY','RI','US Avg','TX','FL'\],datasets:\[\{data:\[)[\d.,]+(\])",
     rf'\g<1>{bar_data}\g<2>', F),

    ("ELEC_MA annual series",
     r'(const ELEC_MA = \[)[^\]]+(\])',
     rf'\g<1>{elec_ma_js}\g<2>', F),

    ("ELEC_US annual series",
     r'(const ELEC_US = \[)[^\]]+(\])',
     rf'\g<1>{elec_us_js}\g<2>', F),
]

original = html
missing = []
for label, pattern, repl, flags in subs:
    html, n = re.subn(pattern, repl, html, flags=flags)
    if n == 0:
        missing.append(label)
        print(f"  MISSING ANCHOR: {label}", file=sys.stderr)
    else:
        print(f"  updated: {label} ({n}x)")

if missing:
    sys.exit(f"\nERROR: {len(missing)} anchor(s) not found — the HTML structure "
             f"changed. Fix the patterns in this script before relying on it. "
             f"Nothing was written.")


# --------------------------------------------------------------------------
# Staleness guard
# --------------------------------------------------------------------------
# The `missing` check above fires only when a KNOWN anchor disappears. It says
# nothing about a figure that never had an anchor -- and that is exactly how this
# page rotted: the S.3143 card sat at 30.21c/$819 and two charts plotted $922
# for months, because no pattern above had ever claimed them.
#
# So: re-read the substituted HTML and assert that every rate and per-year figure
# in the LIVE regions is one this run actually produced. An unrecognised literal
# fails the build instead of shipping.
#
# Adding a genuinely new figure to the page WILL trip this. That is the point --
# it forces a decision about which state the figure is in (derived in-browser,
# anchored to a past moment, or a named constant) rather than letting an unowned
# number quietly drift.

# Regions allowed to carry a vintage other than the latest monthly EIA reading.
FROZEN_REGIONS = (
    # The by-sector table and the industrial-rate alert above it are pinned to
    # their Oct-2025 vintage and labelled as such on the page.
    r'<!-- NEW: Industrial rate premium -->.*?(?=<!-- ===== H\.5151)',
    # Annual history: every past year's rate legitimately lives here.
    r'const ELEC_(?:MA|US) = \[[^\]]*\]',
    # The Equivalence tab is a separate hand-built model (see the note above).
    r'<div id="equivalence" class="tab-content">.*?(?=<!-- ===== BOSTON)',
)

live = html
for _pat in FROZEN_REGIONS:
    live, _n = re.subn(_pat, "", live, flags=re.S)
    if _n == 0:
        sys.exit(f"\nERROR: frozen-region marker not found: {_pat!r}\nThe "
                 f"staleness guard cannot tell live copy from a pinned vintage, "
                 f"so it would raise false alarms. Fix the marker. Nothing was "
                 f"written.")

# Rates this run wrote: the monthly state/US figures, plus the two closed-year
# annual averages on the annual-average card.
allowed_cents = {cents(v) for v in rate.values()} | {cents(ann_ma), cents(ann_us)}

# Per-year dollar figures that are analysis constants rather than EIA output.
# Each is documented where it appears on the page.
allowed_per_yr = {
    dollars(overpay),  # MA overpayment vs the US average -- written by this run
    "150",   # realistic H.5151 relief (Mass Save 80 + ACP 40 + net metering 30)
    "200",   # Boston BCCE supply-only savings, per city program data
    "377",   # untouched policy charges, Cut-vs-Kept tab
    "493",   # S.3143's own claim: $14.3B / 2.9M households / 10 yrs
}

stale = set()
for m in re.finditer(r'(\d+\.\d+)&#x00A2;', live):
    if m.group(1) not in allowed_cents:
        stale.add(f"{m.group(1)}¢")
for m in re.finditer(r'\$([\d,]+)/yr', live):
    if m.group(1) not in allowed_per_yr:
        stale.add(f"${m.group(1)}/yr")

if stale:
    sys.exit(f"\nERROR: stale figure(s) survived the update: "
             f"{', '.join(sorted(stale))}\n"
             f"This run wrote MA {cents(ma)}¢ / US {cents(us)}¢ / "
             f"${dollars(overpay)}/yr ({mon_abbr}). Each figure above sits in a "
             f"live region but is not one this run produced, so no anchor owns "
             f"it. Either add a substitution for it, derive it in-browser from "
             f"the rate table, or move it into a labelled frozen region. "
             f"Nothing was written.")

if html == original:
    print("\nNo changes — dashboard already current.")
else:
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nDone — energy-dashboard.html updated to {mon_abbr} EIA data.")
