#!/usr/bin/env python3
"""
Refresh MLS PIN figures in the MA Data Hub dashboards — history AND current period.

MLS owns every number these pages plot. Two windows, one source:

  history  per CALENDAR YEAR, 2014..prev_year, cached in data/mls-history.json and
           fetched only by --backfill-history.
  tail     the TRAILING-12-MONTH window ending today, refetched on every run.

The two are composed into one series per (market, property type, metric) and written
into the data arrays of ma-housing-dashboard.html and haverhill-market-report.html as
COMPLETE arrays. Nothing on either page is a hand-typed number any more.

Note "trailing 12 months", not YTD: fetch_closed_trailing_12mo() queries
CloseDate >= TRAILING_12MO_START, i.e. a rolling 365-day window ending today. The
docstring used to say YTD and the dashboards inherited the error, labelling a
Jul-2025→Jul-2026 window "2026 YTD" and a 12-month closing count "YTD Sold".

WHY HISTORY IS CACHED RATHER THAN REFETCHED NIGHTLY
A full pass is ~1M closed-sale rows -> ~5,000 paginated requests -> ~20-40min and a
serious dent in the Bridge rate limit. The nightly job needs ~29 queries. Closed
calendar years are also effectively immutable (late restatements are rare and tiny),
so refetching them every night would burn the quota to rewrite identical digits.
data/mls-history.json is therefore THE source: one file, fetched deliberately, from
which both pages' arrays are rendered. Same shape as update-price-distribution.js,
which already writes data/price-distribution-latest.json and injects the same payload.

    python update-mls-figures.py                     # nightly: tail only (cheap)
    python update-mls-figures.py --backfill-history  # fetch missing years (expensive)

--backfill-history is incremental: it fetches only (market, type, year) cells absent
from the cache, so a run that dies partway resumes where it stopped, and January's
rollover costs one year rather than twelve. Nothing is written to the pages unless
every cell for the displayed window is present.

WHAT MLS CANNOT RETURN
Active inventory (`inv`) and months supply (`supply`) are POINT-IN-TIME quantities.
The feed carries a listing's status now, not its status on 2018-12-31, so there is no
query that returns "active listings in 2018" — and reconstructing it from listing
dates would systematically undercount listings that expired and were purged. Those two
series are therefore current-period only; historical slots are null and the pages
render the gap. A short exact series beats a long partly-invented one — inventing them
is precisely the defect this file spent a day undoing.

Requires: BRIDGE_TOKEN env var. No third-party deps (urllib only).
"""

from __future__ import annotations

import argparse
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

_ap = argparse.ArgumentParser(description="Refresh MLS PIN figures in the MA dashboards.")
_ap.add_argument(
    "--backfill-history",
    action="store_true",
    help="Fetch per-calendar-year history for cells missing from data/mls-history.json. "
         "Expensive (~1M rows, ~20-40min). Off by default so the nightly cron stays cheap.",
)
_ap.add_argument(
    "--refetch-year",
    type=int,
    action="append",
    default=[],
    help="Force a re-fetch of this calendar year even if cached. Repeatable.",
)
_ap.add_argument(
    "--history-start",
    type=int,
    default=2014,
    help="First calendar year to carry (default 2014, matching the pages' 13-year window).",
)
ARGS = _ap.parse_args()

TOKEN = os.environ.get("BRIDGE_TOKEN")
if not TOKEN:
    sys.exit("BRIDGE_TOKEN env var not set")

REPO = Path(__file__).resolve().parent
BASE = "https://api.bridgedataoutput.com/api/v2/mlspin/listings"
TODAY = datetime.date.today()
YEAR = TODAY.year
MONTHS_ELAPSED = max(TODAY.month, 1)
TRAILING_12MO_START = (TODAY - datetime.timedelta(days=365)).strftime("%Y-%m-%d")

HISTORY_PATH = REPO / "data" / "mls-history.json"
HIST_START = ARGS.history_start
HIST_END = YEAR - 1  # last COMPLETE calendar year; the current year is the tail
HIST_YEARS = list(range(HIST_START, HIST_END + 1))
# The full x-axis both pages plot: complete calendar years, then the trailing-12mo tail.
SERIES_YEARS = HIST_YEARS + [YEAR]

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
    base = _base_filter(scope, pt)

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


def _base_filter(scope: dict, pt: tuple) -> dict:
    """The one closed-sale filter definition. Every window — trailing-12mo tail and
    each historical calendar year — is this same filter with different CloseDate
    bounds, so the history cannot drift away from the tail by definition. It matches
    update-price-distribution.js field-for-field (StandardStatus=Closed,
    PropertyType/PropertySubType, CloseDate.gte/.lt), which is what lets that file's
    per-year counts act as an independent check on this one's."""
    base = {
        "StandardStatus.in": "Closed",
        "PropertyType.in": pt[0],
        "fields": "ClosePrice,LivingArea,ListPrice,MLSPIN_MARKET_TIME,CloseDate,ListingKey",
    }
    if pt[1]:
        base["PropertySubType.in"] = pt[1]
    base.update(scope)
    return base


def _year_bounds(yr: int) -> tuple[str, str]:
    """[Jan 1, Jan 1 next) for `yr`, clamped to tomorrow — the same calendar-year window
    update-price-distribution.js uses. CloseDate, not list date: a sale belongs to the
    year it CLOSED, which is the convention the tail already uses."""
    start = datetime.date(yr, 1, 1)
    end = datetime.date(yr + 1, 1, 1)
    tomorrow = TODAY + datetime.timedelta(days=1)
    if end > tomorrow:
        end = tomorrow
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _months_in(yr: int) -> list[tuple[str, str]]:
    """Monthly [start, end) windows inside `yr`, for scopes past Bridge's 10k offset cap."""
    out = []
    for m in range(1, 13):
        start = datetime.date(yr, m, 1)
        end = datetime.date(yr + 1, 1, 1) if m == 12 else datetime.date(yr, m + 1, 1)
        tomorrow = TODAY + datetime.timedelta(days=1)
        if start >= tomorrow:
            break
        if end > tomorrow:
            end = tomorrow
        out.append((start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
    return out


def fetch_closed_year(scope: dict, pt: tuple, yr: int) -> list[dict]:
    """Every closed sale in calendar year `yr`. Chunks by month past the 10k offset cap.

    Fails rather than returns short. _paginate_window's offset-cap escape hatch prints a
    WARN and returns partial rows, which is survivable for a headline count but NOT for
    a mean: a truncated page set yields an average silently computed over whichever
    sales happened to sort first, and that number would look completely normal on the
    chart. A short fetch raises; the run writes nothing.
    """
    base = _base_filter(scope, pt)
    start, end = _year_bounds(yr)
    whole = {**base, "CloseDate.gte": start, "CloseDate.lt": end}
    total = _get({**whole, "limit": 1}).get("total", 0)
    if total == 0:
        return []

    rows: list[dict] = []
    seen_keys: set = set()
    if total <= 10000:
        _paginate_window(whole, rows, seen_keys)
        expected = total
    else:
        expected = 0
        for win_start, win_end in _months_in(yr):
            win = {**base, "CloseDate.gte": win_start, "CloseDate.lt": win_end}
            win_total = _get({**win, "limit": 1}).get("total", 0)
            if win_total > 10000:
                raise RuntimeError(
                    f"{yr} {win_start}: {win_total} rows in one month exceeds the 10k "
                    "offset cap — this window needs finer chunking before it can be trusted"
                )
            expected += win_total
            _paginate_window(win, rows, seen_keys)

    if len(rows) < expected:
        raise RuntimeError(
            f"{yr}: fetched {len(rows)} of {expected} rows — refusing to average a "
            "partial year"
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


# ---------- HISTORY CACHE ----------
#
# data/mls-history.json is the source both pages are rendered from. Shape:
#
#   {"meta": {...}, "cells": {"<scope>|<pt>|<year>": {aggregate(), ...}}}
#
# Flat string keys because the cache is addressed one (market, type, year) cell at a
# time and JSON has no tuple keys. A cell is only ever written after its year fetched
# whole, so a present cell is a complete cell — which is what makes resuming safe.
#
# AGGREGATES ONLY — never the rows they were computed from. This file is committed and
# published with the site, and record-level MLS data is licensed, not ours to publish
# (cf. .gitignore's data/_raw_nh/ carve-out for the NH feed's raw cache). Every number
# here is a mean/median/count already displayed on the public pages; the listings behind
# them are fetched, reduced, and dropped. Do not cache rows here to save requests.

PT_BY_LABEL = {"sf": PT_SF, "co": PT_CONDO, "mf": PT_MULTI}


def _cell_key(scope_name: str, pt_label: str, yr: int) -> str:
    return f"{scope_name}|{pt_label}|{yr}"


def load_history() -> dict:
    if not HISTORY_PATH.exists():
        return {"meta": {}, "cells": {}}
    try:
        h = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"[mls-update] data/mls-history.json is corrupt ({e}) — refusing to guess")
    h.setdefault("cells", {})
    h.setdefault("meta", {})
    return h


def backfill_history(history: dict) -> dict:
    """Fetch every (scope, pt, year) cell missing from the cache.

    Incremental by design. A full pass is ~1M rows / ~5k requests / ~20-40min, which is
    survivable once but not nightly, and not something to restart from zero because
    request 4,900 hit a 429. Cells already cached are skipped, so a re-run resumes and
    the annual rollover costs one year instead of twelve.

    Writes the cache after EACH cell rather than at the end: a cell is a complete
    fetched year, so persisting it immediately is what makes the resume real. This is
    separate from the all-or-nothing rule for the PAGES — the cache may be partial and
    still be correct; the pages may not, and are written only when every cell is in.
    """
    todo = [
        (s, p, y)
        for y in HIST_YEARS
        for s in SCOPES
        for p in PT_BY_LABEL
        if _cell_key(s, p, y) not in history["cells"] or y in ARGS.refetch_year
    ]
    if not todo:
        print("[mls-update] history cache complete — nothing to backfill")
        return history

    print(f"[mls-update] backfilling {len(todo)} cell(s) — this is the expensive path")
    for n, (scope_name, pt_label, yr) in enumerate(todo, 1):
        try:
            rows = fetch_closed_year(SCOPES[scope_name], PT_BY_LABEL[pt_label], yr)
        except RuntimeError as e:
            sys.exit(f"[mls-update] history fetch failed for {scope_name}/{pt_label}/{yr}: {e}")
        a = aggregate(rows)
        # A year with no closings is a fact, not a hole to fill. It is cached as an
        # honest zero/None and the page renders the gap. Nothing is interpolated.
        history["cells"][_cell_key(scope_name, pt_label, yr)] = a
        history["meta"] = {
            "generated": TODAY.strftime("%Y-%m-%d"),
            "source": "MLS PIN via Bridge Data Output",
            "window": "closed sales per calendar year, by CloseDate",
            "property_types": {
                "sf": "Residential / Single Family Residence",
                "co": "Residential / Condominium",
                "mf": "Residential Income",
            },
            "years": HIST_YEARS,
            "unavailable": {
                "inv": "active listing counts are point-in-time; MLS cannot return a past year",
                "supply": "derived from active inventory, so likewise current-period only",
            },
        }
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text(json.dumps(history, indent=1), encoding="utf-8")
        print(f"  [{n}/{len(todo)}] {scope_name:<11} {pt_label} {yr}: "
              f"n={a['count']:>5}" + (f" avg=${a['avg_price']:>10,.0f}" if a["avg_price"] else " (no closings)"))
    return history


def history_series(history: dict, scope_name: str, pt_label: str, agg_key: str) -> list | None:
    """The historical values for one metric, oldest-first. None if any year is missing —
    the caller must then leave the page alone rather than publish a series with a hole
    where MLS simply hasn't been asked yet."""
    out = []
    for yr in HIST_YEARS:
        cell = history["cells"].get(_cell_key(scope_name, pt_label, yr))
        if cell is None:
            return None
        out.append(cell.get(agg_key))
    return out


def fhfa_crosscheck(history: dict) -> list[str]:
    """Check the fetched history's SHAPE against an independent house-price index.

    This exists because of a near-miss. Auditing the inherited series, the per-year unit
    counts matched update-price-distribution.js far better when shifted a year (mean
    error 8.5-12.1% -> 1.6-2.3%, consistently across four geographies). It looked
    exactly like an off-by-one. It wasn't: cross-checking the PRICE series against FHFA's
    MA index showed both were correctly labelled (r=+0.79 as-labelled vs ~0.0 shifted),
    and the count "shift" was an autocorrelation artifact — smooth monotone series fit
    well under a shift by coincidence. Acting on it would have corrupted both pages.

    So: unit counts cannot adjudicate alignment; an independent index can. FHFA MASTHPI
    comes from FRED via update-housing-history.js and owes nothing to MLS, so if our
    query window or date field were wrong (calendar-year vs trailing-12mo, list date vs
    close date) the fetched YoY would stop tracking it — and would track it better
    shifted. That is the failure this asserts against.

    Levels aren't comparable (average sale price vs repeat-sales index) but turning
    points are, which is all this needs.
    """
    fred = REPO / "data" / "housing-history-latest.json"
    if not fred.exists():
        return ["FHFA cross-check skipped: data/housing-history-latest.json absent"]
    try:
        obs = json.loads(fred.read_text(encoding="utf-8"))["nominal"]["masthpi"]
    except (json.JSONDecodeError, KeyError) as e:
        return [f"FHFA cross-check skipped: {fred.name} unreadable ({e})"]

    by_year: dict[int, list[float]] = {}
    for o in obs:
        by_year.setdefault(int(o["d"][:4]), []).append(o["v"])
    idx = {y: statistics.mean(v) for y, v in by_year.items()}
    idx_yoy = {y: (idx[y] / idx[y - 1] - 1) * 100 for y in sorted(idx) if y - 1 in idx}

    prices = history_series(history, "ma", "sf", "avg_price")
    if not prices or any(p is None for p in prices):
        return ["FHFA cross-check skipped: MA SF price history incomplete"]
    ours = {
        HIST_YEARS[i]: (prices[i] / prices[i - 1] - 1) * 100
        for i in range(1, len(prices))
        if prices[i - 1]
    }

    def _r(series: dict) -> float | None:
        ks = [k for k in series if k in idx_yoy]
        if len(ks) < 3:
            return None
        a = [series[k] for k in ks]
        b = [idx_yoy[k] for k in ks]
        if len(set(a)) < 2 or len(set(b)) < 2:
            return None
        return statistics.correlation(a, b)

    # Test BOTH directions. Checking only one is a real trap: a series carrying the
    # NEXT year's value (label 2018 holding 2019's sales) scores an unremarkable
    # r=+0.445 as-labelled -- comfortably past any absolute floor -- and is only
    # exposed by the forward shift, which fits it at r=+1.0. A one-sided check waves
    # that straight through. Caught by the stub's STUB_SHIFT_YEARS negative test.
    cands = {
        0: _r(ours),
        -1: _r({y - 1: v for y, v in ours.items()}),
        +1: _r({y + 1: v for y, v in ours.items()}),
    }
    aligned = cands[0]
    if aligned is None:
        return ["FHFA cross-check skipped: not enough overlapping years"]

    def _s(v):
        return "n/a" if v is None else f"{v:+.3f}"

    print(f"[mls-update] FHFA cross-check (MA SF price YoY vs FHFA MA HPI YoY): "
          f"as-labelled r={_s(cands[0])}, back-1yr r={_s(cands[-1])}, fwd-1yr r={_s(cands[+1])}")

    fails = []
    for shift in (-1, +1):
        r = cands[shift]
        if r is not None and r > aligned + 0.15:
            direction = "back" if shift == -1 else "forward"
            fails.append(
                f"fetched MA SF history tracks FHFA BETTER shifted {direction} a year "
                f"(r={r:+.3f}) than as-labelled (r={aligned:+.3f}) — the calendar-year "
                "window or date field is probably wrong. Check _year_bounds/CloseDate."
            )
    if aligned < 0.30:
        fails.append(
            f"fetched MA SF history barely tracks FHFA's MA index (r={aligned:+.3f}). "
            "Expected ~+0.8. The query window is suspect — do not publish this."
        )
    return fails


def months_supply(active: int, closed_12mo: int) -> float | None:
    if not active or not closed_12mo:
        return None
    monthly_rate = closed_12mo / 12.0
    return round(active / monthly_rate, 2) if monthly_rate else None


# ---------- DATA COLLECTION ----------

print(f"[mls-update] year={YEAR}, trailing-12mo from {TRAILING_12MO_START}")

# History first: if it is going to fail, fail before spending the tail's quota.
HISTORY = load_history()
if ARGS.backfill_history:
    HISTORY = backfill_history(HISTORY)

HIST_READY = all(
    history_series(HISTORY, s, p, "avg_price") is not None
    for s in SCOPES
    for p in PT_BY_LABEL
)
if HIST_READY:
    print(f"[mls-update] history cache covers {HIST_START}-{HIST_END} — writing FULL series")
    # Validate the shape before spending the tail's quota, and before touching a page.
    _fhfa_fails = fhfa_crosscheck(HISTORY)
    for _f in _fhfa_fails:
        print(f"  [FHFA] {_f}")
    if any("skipped" not in f for f in _fhfa_fails):
        sys.exit(
            "[mls-update] fetched history failed the independent FHFA shape check — "
            "refusing to publish. This is the off-by-one guard; see fhfa_crosscheck()."
        )
else:
    print(
        f"[mls-update] NOTE: data/mls-history.json does not yet cover {HIST_START}-{HIST_END}. "
        "Writing the trailing-12mo tail only and leaving the inherited historical values "
        "in place. Run with --backfill-history to have MLS take ownership of them."
    )

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


def _fmt_num(v, is_float: bool) -> str:
    if v is None:
        return "null"
    return f"{v:.2f}" if is_float else str(int(round(v)))


def replace_array_full(html: str, path: str, metric: str, values: list, is_float: bool) -> tuple[str, bool]:
    """Replace the WHOLE array literal at `path.metric`, not just its last element.

    This is what "MLS owns the series" means mechanically. replace_array_tail below
    writes one number and leaves twelve alone, which is exactly how two pages came to
    carry different histories of the same metric while agreeing on the only value
    anyone would think to compare. When the history cache is populated, every element
    is written from it and nothing inherited survives.

    A None inside `values` is written as `null` and rendered as a gap. That is load-
    bearing: months supply has no historical value MLS can return, and a gap is the
    honest rendering of "not measured". Do not backfill it with anything.
    """
    span = _resolve_path(html, path)
    if not span:
        return html, False
    lo, hi = span
    pat = re.compile(r"(" + _key_re(metric) + r"\s*:\s*)\[[^\]]*\]")
    m = pat.search(html, lo, hi)
    if not m:
        return html, False
    body = ",".join(_fmt_num(v, is_float) for v in values)
    return html[: m.start()] + m.group(1) + "[" + body + "]" + html[m.end():], True


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


def replace_string_const(html: str, name: str, value: str) -> tuple[str, bool]:
    """Rewrite a single-quoted `var/const NAME = '...'` string declaration.

    Used for HIST_PROV, the sentence each page shows about what its historical years
    ARE. The script writes it because the script is what makes it true or false: a
    hand-typed provenance note has to be edited in lockstep with the data to stay
    honest, and this repo has already demonstrated that it won't be — the arrays spent
    the files' whole lives under a comment reading "from uploaded PDFs" above numbers
    nobody could trace to any PDF. Tying the claim to the writer means the page cannot
    advertise a provenance the data doesn't have.

    `value` must not contain a single quote; callers pass fixed English, so this
    asserts rather than escaping and pretending to be general.
    """
    if "'" in value:
        raise ValueError(f"{name}: apostrophes would break the JS string literal — rephrase")
    pat = re.compile(rf"(\b(?:var|const|let)\s+{re.escape(name)}\s*=\s*')[^']*(')")
    new_html, n = pat.subn(lambda m: m.group(1) + value + m.group(2), html, count=1)
    return new_html, n > 0


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

# The sentence each page shows about its own historical years. It tracks what this run
# actually wrote, so during the transition — script deployed, --backfill-history not yet
# run — the pages keep saying "inherited" instead of claiming an MLS lineage they do not
# have yet. It flips by itself on the run that populates the cache.
# No apostrophes: these are written into single-quoted JS literals (replace_string_const).
HIST_PROV_TEXT = (
    f"Historical years ({HIST_START}-{HIST_END}) are closed-sale aggregates queried from "
    f"MLS PIN per calendar year, cached and refetched only on demand."
    if HIST_READY else
    "Historical years are inherited from the pre-migration dataset and their vintage has "
    "not been re-verified against MLS."
)


# ---------- MA DASHBOARD ----------

ma_changes: list[tuple[str, bool]] = []


# Sentinel: the quantity exists for the current period but MLS cannot return it for a
# past calendar year (see the module docstring — active inventory is point-in-time).
# Its historical slots are written as null, NOT left holding whatever was inherited.
# That distinction is the whole point: "we did not measure this" must not be silently
# represented by someone's old transcription of it.
NO_HISTORY = object()


def _hist_for(scope_name, pt_label, agg_key):
    if agg_key is NO_HISTORY:
        return [None] * len(HIST_YEARS)
    return history_series(HISTORY, scope_name, pt_label, agg_key)


def _arr(html, changes, label, path, metric, value, is_float=True, hist_vals=None):
    """Write `path.metric`. Full series once the history cache is populated; tail-only
    until then, so the nightly cron keeps working through the transition."""
    if HIST_READY and hist_vals is not None:
        html, ok = replace_array_full(html, path, metric, list(hist_vals) + [value], is_float)
        changes.append((f"{label} {path}.{metric} [full]", ok))
    else:
        html, ok = replace_array_tail(html, path, metric, value, is_float=is_float)
        changes.append((f"{label} {path}.{metric}", ok))
    return html


# d.<market> — the 13-year single-family series. Every SF figure on the page (hero,
# overview cards, per-market cards, the 13-year tables, the property-type SF view, the
# whole affordability tab, the Greater Newburyport Newburyport row) is derived from
# these five arrays, so this loop is the entire single-family surface.
MA_MARKET_KEY = {"ma": "ma", "boston": "boston", "essex": "essex", "newburyport": "nbpt"}
MA_METRICS = [
    ("price", "avg_price", True),
    ("sqft", "avg_sqft", True),
    ("dom", "avg_dom", True),
    ("units", "count", False),
    ("supply", NO_HISTORY, True),
]
for scope_name, ma_key in MA_MARKET_KEY.items():
    a = results[scope_name]["sf"]
    tails = {
        "price": a["avg_price"], "sqft": a["avg_sqft"], "dom": a["avg_dom"],
        "units": a["count"], "supply": ms[scope_name],
    }
    for metric, agg_key, is_float in MA_METRICS:
        ma = _arr(ma, ma_changes, "ma-dash", f"d.{ma_key}", metric, tails[metric],
                  is_float=is_float, hist_vals=_hist_for(scope_name, "sf", agg_key))

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
        tails = {
            "price": a["avg_price"], "sqft": a["avg_sqft"], "dom": a["avg_dom"],
            "units": a["count"], "supply": ms_pt[scope_name][pt_label],
        }
        for metric, agg_key, is_float in MA_METRICS:
            ma = _arr(ma, ma_changes, "ma-dash", f"dpt.{ma_key}.{pt_label}", metric,
                      tails[metric], is_float=is_float,
                      hist_vals=_hist_for(scope_name, pt_label, agg_key))

ma, ok = replace_asof(ma, footer_date)
ma_changes.append(("ma-dash DATA_ASOF", ok))

ma, ok = replace_string_const(ma, "HIST_PROV", HIST_PROV_TEXT)
ma_changes.append(("ma-dash HIST_PROV", ok))


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
        hav = _arr(hav, hav_changes, "hav-dash", var, arr_key, val, is_float=is_float,
                   hist_vals=_hist_for(scope, pt_label, agg_key))

# inv/supply: current period only. See NO_HISTORY — MLS has no answer for "how many
# listings were active in 2018", so those slots go null rather than keep the inherited
# numbers that used to sit there.
hav = _arr(hav, hav_changes, "hav-dash", "sf", "inv", active_sf["haverhill"], is_float=False,
           hist_vals=_hist_for("haverhill", "sf", NO_HISTORY))
hav = _arr(hav, hav_changes, "hav-dash", "sf", "supply", ms["haverhill"], is_float=True,
           hist_vals=_hist_for("haverhill", "sf", NO_HISTORY))

# Haverhill condo months supply has no historical series — a scalar, not an array tail.
hav, ok = replace_scalar(hav, "CO_SUPPLY", ms_hav_co, is_float=True)
hav_changes.append(("hav-dash CO_SUPPLY", ok))

hav, ok = replace_asof(hav, footer_date)
hav_changes.append(("hav-dash DATA_ASOF", ok))

hav, ok = replace_string_const(hav, "HIST_PROV", HIST_PROV_TEXT)
hav_changes.append(("hav-dash HIST_PROV", ok))


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


# ---------- CROSS-FILE CONSISTENCY GUARD ----------
#
# The MA and Essex single-family series exist on both pages: as the subject of
# ma-housing-dashboard.html (`d.ma` / `d.essex`) and as benchmark lines on
# haverhill-market-report.html (`ma` / `es`). They are ONE series and must stay one.
#
# They did not used to be. They were two independently transcribed copies that
# disagreed on every historical year -- MA 2018 was 459,802 on the Haverhill report and
# 469,326.80 on the MA dashboard, Essex 2018 was off by $20,763 -- and Haverhill's MA
# 2019-2021 were not measurements at all but round "estimated from trend" placeholders
# drawn as if they were real.
#
# This script is why nobody noticed. It writes the current-period tail into both files
# from a single query, so the one number a reader would think to compare always
# matched, while the twelve behind it did not. The guard closes that: the tails
# agreeing is no longer evidence that the series agree, because now the whole series is
# checked. Reconciling the values was the fix; this is what keeps it fixed.
#
# Note this asserts CONSISTENCY, not correctness. The historical values predate the
# repo (migrated from duncanburns2013-dot/Housing-Market-Data, source extracts never
# committed) and no script here can reproduce them. If they are ever re-derived from
# the source, both files must be updated together -- which is exactly what this
# enforces.

def _read_array(html: str, path: str, metric: str) -> list[str] | None:
    """Every element of `path.metric`'s array literal, as raw tokens."""
    span = _resolve_path(html, path)
    if not span:
        return None
    lo, hi = span
    m = re.search(_key_re(metric) + r"\s*:\s*\[([^\]]*)\]", html[lo:hi])
    if not m:
        return None
    return [tok.strip() for tok in m.group(1).split(",")]


def _num_eq(a: str, b: str) -> bool:
    if a == "null" or b == "null":
        return a == b
    try:
        return abs(float(a) - float(b)) < 0.01
    except ValueError:
        return False


SHARED_SERIES = [("ma", "d.ma"), ("es", "d.essex")]
drift = []
for hav_var, ma_path in SHARED_SERIES:
    for metric in ("price", "sqft", "dom"):
        a = _read_array(hav, hav_var, metric)
        b = _read_array(ma, ma_path, metric)
        if a is None or b is None:
            drift.append(
                f"{hav_var}.{metric}: unreadable "
                f"(hav={'ok' if a else 'MISSING'}, ma={'ok' if b else 'MISSING'})"
            )
            continue
        if len(a) != len(b):
            drift.append(
                f"{hav_var}.{metric}: length {len(a)} (haverhill) vs {len(b)} (ma-housing)"
            )
            continue
        for i, (x, y) in enumerate(zip(a, b)):
            if not _num_eq(x, y):
                drift.append(
                    f"{hav_var}.{metric}[{i}]: haverhill {x} vs ma-housing {y}"
                )

if drift:
    print("\n[mls-update] SHARED-SERIES DRIFT (haverhill vs ma-housing):")
    for f in drift:
        print(f"  [DRIFT] {f}")


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
if misses or verify_fails or drift:
    sys.exit(
        f"[mls-update] {misses} substitution(s) missed, "
        f"{len(verify_fails)} read-back failure(s), "
        f"{len(drift)} shared-series drift(s) — dashboards NOT updated cleanly. "
        "Check the HTML data blocks for structural drift."
    )
