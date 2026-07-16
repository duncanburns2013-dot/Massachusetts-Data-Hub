#!/usr/bin/env python3
"""
Refresh current-period MLS PIN figures in the MA Data Hub dashboards.

Pulls TRAILING-12-MONTH closed-sale aggregates from Bridge MLS PIN and writes them into
the data arrays of ma-housing-dashboard.html, haverhill-market-report.html, and
MASTER_DATA.md. Historical years (2014..prev_year) are not modified.

Note "trailing 12 months", not YTD: fetch_closed_trailing_12mo() queries
CloseDate >= TRAILING_12MO_START, i.e. a rolling 365-day window ending today. The
docstring used to say YTD and the dashboards inherited the error, labelling a
Jul-2025→Jul-2026 window "2026 YTD" and a 12-month closing count "YTD Sold".

This script writes DATA ARRAYS ONLY. The pages derive every displayed figure from
those arrays at render time — see the PROSE DERIVATION block at the foot of each. Do
not add regex patches for individual cards here; that is the defect this structure
exists to prevent (see the note above replace_array_tail).

Requires: BRIDGE_TOKEN env var. No third-party deps (urllib only).
"""

from __future__ import annotations

import datetime
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN = os.environ.get("BRIDGE_TOKEN")
if not TOKEN:
    sys.exit("BRIDGE_TOKEN env var not set")

REPO = Path(__file__).resolve().parent
BASE = "https://api.bridgedataoutput.com/api/v2/mlspin/listings"
TODAY = datetime.date.today()
YEAR = TODAY.year
MONTHS_ELAPSED = max(TODAY.month, 1)
TRAILING_12MO_START = (TODAY - datetime.timedelta(days=365)).strftime("%Y-%m-%d")

PT_SF = ("Residential", "Single Family Residence")
PT_CONDO = ("Residential", "Condominium")
PT_MULTI = ("Residential Income", None)

SCOPES = {
    "haverhill": {"City.in": "Haverhill"},
    "boston": {"City.in": "Boston"},
    "newburyport": {"City.in": "Newburyport"},
    "essex": {"CountyOrParish.in": "Essex"},
    "ma": {"StateOrProvince.in": "MA"},
}


# Bridge rate-limits on a ~1-minute rolling window. Space calls out slightly so
# a big statewide pass doesn't burst straight through the quota in a few seconds.
_MIN_REQUEST_INTERVAL = 0.25  # seconds
_last_request_ts = 0.0


def _throttle() -> None:
    global _last_request_ts
    delta = time.time() - _last_request_ts
    if delta < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - delta)
    _last_request_ts = time.time()


def _wait_after_429(e: urllib.error.HTTPError, body: str, attempt: int) -> float:
    """Seconds to wait after a 429. Prefer Bridge's own reset signal — the
    Retry-After header or the reset timestamp embedded in the body — over blind
    exponential backoff, which is far too short to outlast the rolling window
    (the body says e.g. 'Your limit will reset on Wed Jul 08 2026 10:54:32 GMT+0000')."""
    retry_after = e.headers.get("Retry-After") if e.headers else None
    if retry_after:
        try:
            return min(float(retry_after) + 1.0, 120.0)
        except ValueError:
            pass  # HTTP-date form is rare here; fall through to body parsing
    m = re.search(r"reset on (.+?)\s*\(", body)
    if m:
        try:
            reset = datetime.datetime.strptime(
                m.group(1).strip(), "%a %b %d %Y %H:%M:%S GMT%z"
            )
            secs = (reset - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
            if secs > 0:
                return min(secs + 3.0, 120.0)
        except ValueError:
            pass
    return min(2 ** attempt + 0.5 * attempt, 60.0)


def _get(params: dict, max_retries: int = 8) -> dict:
    """GET Bridge with backoff on 429/5xx. Bridge rate-limits aggressively when
    we burst through many queries; on 429 we wait for the window it tells us to,
    so one stray rate-limit no longer fails the whole nightly cron."""
    qs = urllib.parse.urlencode(params)
    url = f"{BASE}?{qs}"
    last_err = None
    for attempt in range(max_retries):
        _throttle()
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:400]
            last_err = f"HTTP {e.code}: {body}"
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                if e.code == 429:
                    wait = _wait_after_429(e, body, attempt)
                else:
                    wait = min(2 ** attempt + 0.5 * attempt, 60.0)
                print(f"  [retry] {e.code} on Bridge call — sleeping {wait:.1f}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            sys.exit(f"Bridge HTTP {e.code}: {body}")
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = str(e)
            if attempt < max_retries - 1:
                wait = min(2 ** attempt, 60.0)
                print(f"  [retry] network error — sleeping {wait:.1f}s")
                time.sleep(wait)
                continue
            sys.exit(f"Bridge network error: {last_err}")
    sys.exit(f"Bridge unreachable after {max_retries} retries: {last_err}")


def _monthly_windows() -> list[tuple[str, str]]:
    """Newest-first monthly [start, end) windows covering the last ~365 days.
    Only needed for scopes too large to page within Bridge's 10k offset cap."""
    windows: list[tuple[str, str]] = []
    end = TODAY
    for _ in range(13):
        start = (end.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
        if (TODAY - start).days > 365 + 31:
            start = TODAY - datetime.timedelta(days=365)
        windows.append((start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
        end = start
        if (TODAY - start).days >= 365:
            break
    return windows


def _paginate_window(win_filter: dict, rows: list[dict], seen_keys: set) -> int:
    """Page one CloseDate window into `rows`, deduped by ListingKey. Returns total."""
    offset = 0
    total = 0
    while True:
        out = _get({**win_filter, "limit": 200, "offset": offset})
        total = out.get("total", 0)
        bundle = out.get("bundle") or []
        if not bundle:
            break
        for r in bundle:
            k = r.get("ListingKey")
            if k and k not in seen_keys:
                seen_keys.add(k)
                rows.append(r)
        offset += 200
        if offset >= total:
            break
        if offset > 9800:
            print(f"  WARN: {win_filter.get('CloseDate.gte')} window hit offset cap "
                  f"with {total} total — partial")
            break
    return total


def fetch_closed_trailing_12mo(scope: dict, pt: tuple) -> list[dict]:
    """Trailing 365 days of closed sales. A single paginated pass covers most
    scopes; only those exceeding Bridge's 10k offset cap (statewide) are chunked
    by month. Fetching the whole window in one pass — instead of 13 monthly
    queries per scope — cuts request volume ~5x and keeps us under the rate limit."""
    base = {
        "StandardStatus.in": "Closed",
        "PropertyType.in": pt[0],
        "fields": "ClosePrice,LivingArea,ListPrice,MLSPIN_MARKET_TIME,CloseDate,ListingKey",
    }
    if pt[1]:
        base["PropertySubType.in"] = pt[1]
    base.update(scope)

    whole = {
        **base,
        "CloseDate.gte": TRAILING_12MO_START,
        "CloseDate.lt": TODAY.strftime("%Y-%m-%d"),
    }
    total = _get({**whole, "limit": 1}).get("total", 0)

    rows: list[dict] = []
    seen_keys: set = set()
    if total <= 10000:
        _paginate_window(whole, rows, seen_keys)
    else:
        for win_start, win_end in _monthly_windows():
            _paginate_window(
                {**base, "CloseDate.gte": win_start, "CloseDate.lt": win_end},
                rows,
                seen_keys,
            )
    return rows


def fetch_active_count(scope: dict, pt: tuple) -> int:
    f = {
        "StandardStatus.in": "Active",
        "PropertyType.in": pt[0],
        "limit": 1,
        "fields": "ListingId",
    }
    if pt[1]:
        f["PropertySubType.in"] = pt[1]
    f.update(scope)
    return _get(f).get("total", 0)


def aggregate(rows: list[dict]) -> dict:
    prices = [r["ClosePrice"] for r in rows if r.get("ClosePrice")]
    sqfts = [
        r["ClosePrice"] / r["LivingArea"]
        for r in rows
        if r.get("ClosePrice") and r.get("LivingArea") and r["LivingArea"] > 0
    ]
    doms = [
        r["MLSPIN_MARKET_TIME"]
        for r in rows
        if r.get("MLSPIN_MARKET_TIME") is not None
    ]
    ratios = [
        r["ClosePrice"] / r["ListPrice"]
        for r in rows
        if r.get("ClosePrice") and r.get("ListPrice")
    ]
    return {
        "count": len(rows),
        "avg_price": round(statistics.mean(prices), 2) if prices else None,
        "median_price": round(statistics.median(prices)) if prices else None,
        "avg_sqft": round(statistics.mean(sqfts), 2) if sqfts else None,
        "avg_dom": round(statistics.mean(doms), 1) if doms else None,
        "sp_lp_pct": round(statistics.mean(ratios) * 100, 2) if ratios else None,
    }


def months_supply(active: int, closed_12mo: int) -> float | None:
    if not active or not closed_12mo:
        return None
    monthly_rate = closed_12mo / 12.0
    return round(active / monthly_rate, 2) if monthly_rate else None


# ---------- DATA COLLECTION ----------

print(f"[mls-update] year={YEAR}, trailing-12mo from {TRAILING_12MO_START}")

results: dict[str, dict[str, dict]] = {}
for scope_name, scope in SCOPES.items():
    results[scope_name] = {}
    for pt_label, pt in [("sf", PT_SF), ("co", PT_CONDO), ("mf", PT_MULTI)]:
        rows = fetch_closed_trailing_12mo(scope, pt)
        a = aggregate(rows)
        results[scope_name][pt_label] = a
        line = f"  {scope_name:<11} {pt_label}: n={a['count']:>5}"
        if a["avg_price"]:
            line += f" avg=${a['avg_price']:>10,.0f}"
        if a["avg_dom"] is not None:
            line += f" dom={a['avg_dom']}"
        print(line)

# Active inventory for months supply. SF for every scope; condo/multi as well, because
# the MA dashboard's property-type breakdown shows a Months Supply column for all three
# and nothing was fetching the condo/multi side of it.
active_sf = {
    name: fetch_active_count(scope, PT_SF) for name, scope in SCOPES.items()
}
active_co_hav = fetch_active_count(SCOPES["haverhill"], PT_CONDO)
print(f"  active SF: {active_sf}, active condo haverhill: {active_co_hav}")

# Months supply (SF, by market)
ms = {
    name: months_supply(active_sf[name], results[name]["sf"]["count"])
    for name in SCOPES
}
ms_hav_co = months_supply(active_co_hav, results["haverhill"]["co"]["count"])

# Months supply for condo/multi, for the four markets the MA dashboard charts.
PT_LOOKUP = {"co": PT_CONDO, "mf": PT_MULTI}
ms_pt: dict[str, dict[str, float | None]] = {}
for name in ("ma", "boston", "essex", "newburyport"):
    ms_pt[name] = {}
    for pt_label, pt_spec in PT_LOOKUP.items():
        active = fetch_active_count(SCOPES[name], pt_spec)
        ms_pt[name][pt_label] = months_supply(active, results[name][pt_label]["count"])
print(f"  months supply (condo/multi): {ms_pt}")


# ---------- HTML SUBSTITUTION HELPERS ----------
#
# The updater writes DATA ARRAYS AND NOTHING ELSE.
#
# It used to also reach into the markup and rewrite ~20 card headlines with a regex
# apiece (patch_overview_card / patch_pt_card / patch_ma_hero / patch_hav_hero /
# patch_hav_snapshot). Two things went wrong with that, and both are now structural
# rather than a matter of adding more patterns:
#
#   1. Partial coverage read as full coverage. Anything without a pattern -- table
#      columns, every "Change"/"YoY" cell, prose, the affordability panels -- silently
#      kept whatever was typed at the last hand edit. The data is trailing-365-days, so
#      a page last touched in April contradicted itself in ~40 places by mid-July while
#      `misses` reported all-OK.
#   2. A patched headline and an unpatched copy of the same series could disagree, and
#      did: clicking a property-type toggle re-read the stale `pt` literal and
#      overwrote the statewide card the script had just written correctly.
#
# The pages now derive every displayed figure from the arrays at render time, so this
# script's whole job is to keep the array tails true. If a substitution misses, the
# page is stale and the run fails loudly instead of publishing a half-updated page.


def _money_full(v):
    """$865,741 — used only by the MASTER_DATA.md tables, which are markdown, not HTML."""
    return f"${round(v):,}" if v is not None else None


def fmt_dom(d):
    return None if d is None else str(round(d))


def _key_re(key: str) -> str:
    """Match a JS object key whether or not it is quoted.

    Both forms are live in these files: `d` is authored with bare keys (price:[…]) and
    `dpt` is machine-emitted JSON with quoted ones ("price": […]). The original anchor
    only ever matched the bare form, which is the whole reason `pt` went un-updated for
    the life of the file. Everything that addresses a key goes through here so that
    cannot silently recur.
    """
    return rf'(?:\b{re.escape(key)}\b|"{re.escape(key)}")'


def _tail_re(metric: str) -> str:
    """Match `metric: [ …, LAST ]` and capture LAST (a number or null)."""
    return _key_re(metric) + r'\s*:\s*\[[^\]]*?,\s*(-?\d+(?:\.\d+)?|null)\s*\]'


def _object_span(html: str, key: str, start: int = 0, end: int | None = None):
    """Byte span of the object literal introduced by `key:` / `key =` / `"key":`.

    Brace-matched, so the scan stops at the container's own closing brace and cannot
    wander into a sibling. Returns (open_idx, close_idx) or None.

    The old anchor was a bare regex -- rf"\\b{var}\\s*[:=]\\s*\\{{" -- with the metric
    array matched by [^{}]*? after it. That could not express "the `ma` inside `d`" as
    distinct from "the `ma` inside `pt`", and it could not match a quoted key at all,
    which is exactly why every write landed in `d` and none in `pt`. Nothing logged a
    MISS because the script never tried.
    """
    region_end = len(html) if end is None else end
    m = re.compile(_key_re(key) + r'\s*[:=]\s*\{').search(html, start, region_end)
    if not m:
        return None
    open_idx = m.end() - 1
    depth = 0
    for j in range(open_idx, region_end):
        c = html[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return open_idx, j + 1
    return None


def _resolve_path(html: str, path: str):
    """Resolve a dotted path ('d.ma', 'dpt.nbpt.mf', 'sf') to the span of its object."""
    lo, hi = 0, len(html)
    for seg in path.split("."):
        span = _object_span(html, seg, lo, hi)
        if not span:
            return None
        lo, hi = span
    return lo, hi


def replace_array_tail(html: str, path: str, metric: str, new_value, is_float: bool) -> tuple[str, bool]:
    """Replace the rightmost (current-period) value of `path.metric`'s array literal.

    `path` is dotted and each segment is brace-matched, so 'd.ma' and 'dpt.ma' address
    different objects that both have an `ma` key -- which the old single-anchor form
    could not do.

    A None value writes `null` rather than skipping. A market with no closings in the
    trailing year is a fact the page can render ('—'); silently leaving last year's
    number there is not. The tail pattern accepts `null` back, so the cell re-fills on
    the next run that has data.
    """
    span = _resolve_path(html, path)
    if not span:
        return html, False
    lo, hi = span
    repl = "null" if new_value is None else (
        f"{new_value:.2f}" if is_float else str(int(round(new_value)))
    )
    m = re.compile(_tail_re(metric)).search(html, lo, hi)
    if not m:
        return html, False
    return html[: m.start(1)] + repl + html[m.end(1):], True


def replace_scalar(html: str, name: str, new_value, is_float: bool) -> tuple[str, bool]:
    """Replace a bare `var name=<number>;` / `const name = <number>;` declaration."""
    if new_value is None:
        return html, False
    repl = f"{new_value:.2f}" if is_float else str(int(round(new_value)))
    pat = re.compile(rf'(\b(?:var|const|let)\s+{re.escape(name)}\s*=\s*)(-?\d+(?:\.\d+)?|null)')
    m = pat.search(html)
    if not m:
        return html, False
    return html[: m.start(2)] + repl + html[m.end(2):], True


def replace_asof(html: str, stamp: str) -> tuple[str, bool]:
    """Rewrite the page's single DATA_ASOF vintage stamp.

    Both pages used to carry the date in three or four places -- a hero stamp, a footer
    stamp, and prose like "YTD as of April 25" / "Data as of April 25, 2026". The
    script patched the first two by regex and had no pattern for the prose, so the
    footer advanced to today while the labels beside the same numbers still said April.
    One constant now; the pages read it for every date they show.
    """
    pat = re.compile(r"(\b(?:var|const)\s+DATA_ASOF\s*=\s*')[^']*(')")
    new_html, n = pat.subn(lambda m: m.group(1) + stamp + m.group(2), html, count=1)
    return new_html, n > 0


# ---------- LOAD FILES ----------

HAV = REPO / "haverhill-market-report.html"
MA = REPO / "ma-housing-dashboard.html"
MD = REPO / "MASTER_DATA.md"

hav = HAV.read_text(encoding="utf-8")
ma = MA.read_text(encoding="utf-8")
md = MD.read_text(encoding="utf-8")

footer_date = TODAY.strftime("%B %d, %Y")


# ---------- MA DASHBOARD ----------

ma_changes: list[tuple[str, bool]] = []


def _arr(html, changes, label, path, metric, value, is_float=True):
    html, ok = replace_array_tail(html, path, metric, value, is_float=is_float)
    changes.append((f"{label} {path}.{metric}", ok))
    return html


# d.<market> — the 13-year single-family series. Every SF figure on the page (hero,
# overview cards, per-market cards, the 13-year tables, the property-type SF view, the
# whole affordability tab, the Greater Newburyport Newburyport row) is derived from
# these five arrays, so this loop is the entire single-family surface.
MA_MARKET_KEY = {"ma": "ma", "boston": "boston", "essex": "essex", "newburyport": "nbpt"}
for scope_name, ma_key in MA_MARKET_KEY.items():
    a = results[scope_name]["sf"]
    pairs = [
        ("price", a["avg_price"]),
        ("sqft", a["avg_sqft"]),
        ("dom", a["avg_dom"]),
        ("units", a["count"]),
        ("supply", ms[scope_name]),
    ]
    for metric, val in pairs:
        ma = _arr(ma, ma_changes, "ma-dash", f"d.{ma_key}", metric, val)

# dpt.<market>.<co|mf> — the 5-year condominium and multi-family series.
#
# This is new. `pt` used to hold a copy of all three property types and the script
# never wrote any of it: its anchor could not match a quoted key, so the condo/multi
# arrays had been frozen since the file was written, and the SF copy leaked over the
# correct card whenever a toggle was clicked. `dpt` now holds condo/multi only (SF is
# read from `d`) and is addressed by an explicit container path.
for scope_name, ma_key in MA_MARKET_KEY.items():
    for pt_label in ("co", "mf"):
        a = results[scope_name][pt_label]
        pairs = [
            ("price", a["avg_price"]),
            ("sqft", a["avg_sqft"]),
            ("dom", a["avg_dom"]),
            ("units", a["count"]),
            ("supply", ms_pt[scope_name][pt_label]),
        ]
        for metric, val in pairs:
            ma = _arr(ma, ma_changes, "ma-dash", f"dpt.{ma_key}.{pt_label}", metric, val)

ma, ok = replace_asof(ma, footer_date)
ma_changes.append(("ma-dash DATA_ASOF", ok))


# ---------- HAVERHILL DASHBOARD ----------

hav_changes: list[tuple[str, bool]] = []

HAV_ARRS = [
    ("sf", "haverhill", "sf", [
        ("price", "avg_price", True),
        ("sqft", "avg_sqft", True),
        ("dom", "avg_dom", True),
        ("sold", "count", False),
        # sp_lp_pct was already computed for every scope and only ever written to
        # MASTER_DATA.md, so the SP/LP row of the Full Data table had no live backing
        # and its current-year cell sat frozen. It is a series on the page now.
        ("splp", "sp_lp_pct", True),
    ]),
    ("co", "haverhill", "co", [
        ("price", "avg_price", True),
        ("sqft", "avg_sqft", True),
        ("dom", "avg_dom", True),
        ("sold", "count", False),
    ]),
    ("mf", "haverhill", "mf", [
        ("price", "avg_price", True),
        ("sqft", "avg_sqft", True),
        ("dom", "avg_dom", True),
        ("sold", "count", False),
    ]),
    ("es", "essex", "sf", [
        ("price", "avg_price", True),
        ("sqft", "avg_sqft", True),
        ("dom", "avg_dom", True),
    ]),
    ("ma", "ma", "sf", [
        ("price", "avg_price", True),
        ("sqft", "avg_sqft", True),
        ("dom", "avg_dom", True),
    ]),
]

for var, scope, pt_label, fields in HAV_ARRS:
    for arr_key, agg_key, is_float in fields:
        val = results[scope][pt_label].get(agg_key)
        hav = _arr(hav, hav_changes, "hav-dash", var, arr_key, val, is_float=is_float)

hav = _arr(hav, hav_changes, "hav-dash", "sf", "inv", active_sf["haverhill"], is_float=False)
hav = _arr(hav, hav_changes, "hav-dash", "sf", "supply", ms["haverhill"], is_float=True)

# Haverhill condo months supply has no historical series — a scalar, not an array tail.
hav, ok = replace_scalar(hav, "CO_SUPPLY", ms_hav_co, is_float=True)
hav_changes.append(("hav-dash CO_SUPPLY", ok))

hav, ok = replace_asof(hav, footer_date)
hav_changes.append(("hav-dash DATA_ASOF", ok))


# ---------- MASTER_DATA.md ----------

md_changes = []

def md_replace(text, pattern, repl, label):
    new_text, n = re.subn(pattern, repl, text, count=1)
    md_changes.append((label, n > 0))
    return new_text


# MA 5-year appreciation table — current-year row (all four markets: MA,
# Essex, Boston, Newburyport). The current-year figure is a trailing-12mo proxy
# for the in-progress year. If the annual rollover hasn't added the row yet
# (e.g. first run of a new year), insert it after the newest historical row so
# it is maintained from then on — otherwise the row silently goes stale all year.
_appr_cells = [
    _money_full(results[s]["sf"]["avg_price"])
    for s in ("ma", "essex", "boston", "newburyport")
]
if all(_appr_cells):
    appr_row = f"| {YEAR} | " + " | ".join(_appr_cells) + " |"
    cur_pat = rf"^\| {YEAR} \| \$[\d,]+ \| \$[\d,]+ \| \$[\d,]+ \| \$[\d,]+ \|$"
    prev_pat = rf"^\| {YEAR - 1} \| \$[\d,]+ \| \$[\d,]+ \| \$[\d,]+ \| \$[\d,]+ \|$"
    if re.search(cur_pat, md, flags=re.MULTILINE):
        md, n = re.subn(cur_pat, lambda m: appr_row, md, count=1, flags=re.MULTILINE)
        md_changes.append((f"MASTER_DATA MA {YEAR} appreciation row", n > 0))
    else:
        md, n = re.subn(prev_pat, lambda m: m.group(0) + "\n" + appr_row, md, count=1, flags=re.MULTILINE)
        md_changes.append((f"MASTER_DATA MA {YEAR} appreciation row (inserted)", n > 0))

# MA Avg DOM
if results["ma"]["sf"]["avg_dom"] is not None:
    md = md_replace(
        md,
        r"(\| Avg DOM \| )\d+(?:\.\d+)? days(\s*\| MLS PIN)",
        rf"\g<1>{fmt_dom(results['ma']['sf']['avg_dom'])} days\g<2>",
        "MASTER_DATA MA DOM",
    )

# MA SP/LP Ratio
if results["ma"]["sf"]["sp_lp_pct"] is not None:
    md = md_replace(
        md,
        r"(\| SP/LP Ratio \| )\d+\.\d+%(\s*\| MLS PIN)",
        rf"\g<1>{results['ma']['sf']['sp_lp_pct']}%\g<2>",
        "MASTER_DATA MA SP/LP",
    )

# MA Units Sold (trailing-12mo count)
md = md_replace(
    md,
    r"(\| Units Sold \| )[\d,]+(\s*\| MLS PIN)",
    rf"\g<1>{results['ma']['sf']['count']:,}\g<2>",
    "MASTER_DATA MA Units Sold",
)

# Haverhill Condo median
md = md_replace(
    md,
    r"(\| Condo median \(Haverhill\) \| )\$[\d,]+(\s*\| MLS)",
    rf"\g<1>{_money_full(results['haverhill']['co']['median_price'])}\g<2>",
    "MASTER_DATA Haverhill condo median",
)

# Haverhill SF median
md = md_replace(
    md,
    r"(\| SF median \(Haverhill\) \| )\$[\d,]+(\s*\| MLS)",
    rf"\g<1>{_money_full(results['haverhill']['sf']['median_price'])}\g<2>",
    "MASTER_DATA Haverhill SF median",
)

# Update "Last Updated" date at top of MASTER_DATA.md
md = md_replace(
    md,
    r"(> \*\*Last Updated:\*\* )[A-Z][a-z]+ \d+, \d{4}",
    rf"\g<1>{footer_date}",
    "MASTER_DATA Last Updated",
)


# ---------- WRITE FILES ----------

HAV.write_text(hav, encoding="utf-8")
MA.write_text(ma, encoding="utf-8")
MD.write_text(md, encoding="utf-8")


# ---------- REPORT + GUARD ----------

all_changes = ma_changes + hav_changes + md_changes

print("\n[mls-update] Substitution report:")
for label, ok in all_changes:
    marker = "OK" if ok else "MISS"
    print(f"  [{marker:>4}] {label}")

# Post-substitution guard: read every managed array tail back out of the file we just
# wrote and assert it is the value we meant to write.
#
# `misses` alone only ever caught PATTERN drift — a regex that stopped matching. It
# could not catch a pattern that matched the WRONG place, which is what happened for
# months: the anchor for `pt`'s arrays matched `d`'s instead, so the script reported
# every substitution OK while `pt` had not been touched since the file was authored.
# Reading the value back distinguishes "wrote it" from "thought it wrote it".
def _verify(html: str, path: str, metric: str, expected) -> bool:
    span = _resolve_path(html, path)
    if not span:
        return False
    lo, hi = span
    m = re.search(_tail_re(metric), html[lo:hi])
    if not m:
        return False
    got = m.group(1)
    if expected is None:
        return got == "null"
    return got != "null" and abs(float(got) - float(expected)) < 0.01


verify_fails = []
for scope_name, ma_key in MA_MARKET_KEY.items():
    a = results[scope_name]["sf"]
    for metric, val in [("price", a["avg_price"]), ("sqft", a["avg_sqft"]),
                        ("dom", a["avg_dom"]), ("units", a["count"]),
                        ("supply", ms[scope_name])]:
        want = val if metric != "units" else (None if val is None else round(val))
        if not _verify(ma, f"d.{ma_key}", metric, want):
            verify_fails.append(f"ma-dash d.{ma_key}.{metric}")
    for pt_label in ("co", "mf"):
        b = results[scope_name][pt_label]
        for metric, val in [("price", b["avg_price"]), ("sqft", b["avg_sqft"]),
                            ("dom", b["avg_dom"]), ("units", b["count"]),
                            ("supply", ms_pt[scope_name][pt_label])]:
            want = val if metric != "units" else (None if val is None else round(val))
            if not _verify(ma, f"dpt.{ma_key}.{pt_label}", metric, want):
                verify_fails.append(f"ma-dash dpt.{ma_key}.{pt_label}.{metric}")

for var, scope, pt_label, fields in HAV_ARRS:
    for arr_key, agg_key, _is_float in fields:
        if not _verify(hav, var, arr_key, results[scope][pt_label].get(agg_key)):
            verify_fails.append(f"hav-dash {var}.{arr_key}")

if verify_fails:
    print("\n[mls-update] READ-BACK FAILED for:")
    for f in verify_fails:
        print(f"  [FAIL] {f}")

misses = sum(1 for _, ok in all_changes if not ok)
print("\n[mls-update] Done.")

# Fail the run rather than publish a page that is stale in a way nobody can see. Every
# figure the pages show is derived from these arrays, so an array the script could not
# write means published numbers that silently disagree with each other — the exact
# failure mode this whole structure exists to prevent. A loud red run is recoverable;
# twelve weeks of quiet drift is what we just spent a day undoing.
if misses or verify_fails:
    sys.exit(
        f"[mls-update] {misses} substitution(s) missed, "
        f"{len(verify_fails)} read-back failure(s) — dashboards NOT updated cleanly. "
        "Check the HTML data blocks for structural drift."
    )
