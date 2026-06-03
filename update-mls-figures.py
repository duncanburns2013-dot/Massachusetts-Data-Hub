#!/usr/bin/env python3
"""
Refresh current-year MLS PIN figures in the MA Data Hub dashboards.

Pulls YTD closed-sale aggregates from Bridge MLS PIN and substitutes them
in-place in ma-housing-dashboard.html, haverhill-market-report.html, and
MASTER_DATA.md. Historical years (2014..prev_year) are not modified.

Requires: BRIDGE_TOKEN env var. No third-party deps (urllib only).
"""

from __future__ import annotations

import datetime
import json
import os
import re
import statistics
import sys
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


def _get(params: dict, max_retries: int = 5) -> dict:
    """GET Bridge with backoff on 429/5xx. Bridge rate-limits aggressively when
    we burst through ~1k monthly-window queries; without retry one stray 429
    fails the whole nightly cron."""
    import time as _time
    qs = urllib.parse.urlencode(params)
    url = f"{BASE}?{qs}"
    last_err = None
    for attempt in range(max_retries):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:400]
            last_err = f"HTTP {e.code}: {body}"
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                wait = 2 ** attempt + (0.5 * attempt)
                print(f"  [retry] {e.code} on Bridge call — sleeping {wait:.1f}s (attempt {attempt+1}/{max_retries})")
                _time.sleep(wait)
                continue
            sys.exit(f"Bridge HTTP {e.code}: {body}")
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = str(e)
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  [retry] network error — sleeping {wait:.1f}s")
                _time.sleep(wait)
                continue
            sys.exit(f"Bridge network error: {last_err}")
    sys.exit(f"Bridge unreachable after {max_retries} retries: {last_err}")


def fetch_closed_trailing_12mo(scope: dict, pt: tuple) -> list[dict]:
    """Trailing 365 days of closed sales. Bridge caps offset at 10000, so we chunk
    by month if needed — each month-window paginated separately."""
    base = {
        "StandardStatus.in": "Closed",
        "PropertyType.in": pt[0],
        "fields": "ClosePrice,LivingArea,ListPrice,MLSPIN_MARKET_TIME,CloseDate",
    }
    if pt[1]:
        base["PropertySubType.in"] = pt[1]
    base.update(scope)

    # Build monthly date windows covering last 365 days (newest first)
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

    rows: list[dict] = []
    seen_keys = set()
    for win_start, win_end in windows:
        win_filter = {
            **base,
            "CloseDate.gte": win_start,
            "CloseDate.lt": win_end,
            "fields": base["fields"] + ",ListingKey",
        }
        offset = 0
        while True:
            out = _get({**win_filter, "limit": 200, "offset": offset})
            if not out["bundle"]:
                break
            for r in out["bundle"]:
                k = r.get("ListingKey")
                if k and k not in seen_keys:
                    seen_keys.add(k)
                    rows.append(r)
            offset += 200
            if offset >= out.get("total", 0):
                break
            if offset > 9800:
                print(
                    f"  WARN: {scope}/{pt[0]}/{pt[1]} window {win_start}..{win_end} "
                    f"hit offset cap with {out['total']} total — partial"
                )
                break
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

# Active SF inventory for months supply (SF only — that's what dashboards show)
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


# ---------- HTML SUBSTITUTION HELPERS ----------

def _money_k(v):
    """Format $X K-style: 610171 -> $610K, 1320379 -> $1320K, 1.1M -> $1.10M."""
    if v is None:
        return None
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    return f"${round(v/1000)}K"


def _money_full(v):
    return f"${round(v):,}" if v is not None else None


def replace_array_tail(html: str, var: str, metric: str, new_value, is_float: bool) -> tuple[str, bool]:
    """
    Replace the rightmost (current-year) value in a JS array literal.
    Works for both `var sf={price:[...,X],...}` and `ma:{price:[...,X],...}` styles.
    Returns (new_html, replaced).
    """
    if new_value is None:
        return html, False
    repl = f"{new_value:.2f}" if is_float else str(int(round(new_value)))
    # Anchor the variable name, then locate the metric array within its {...} object,
    # then replace the last numeric element. Allow .price or price (the var path).
    if "." in var:
        head, tail = var.split(".", 1)
        anchor = rf"\b{re.escape(tail)}\s*[:=]\s*\{{"
    else:
        anchor = rf"\b{re.escape(var)}\s*[:=]\s*\{{"
    # Pattern: anchor ... metric:[ ... , LAST_NUM ]
    pat = anchor + rf"[^{{}}]*?\b{re.escape(metric)}\s*:\s*\[[^\]]*?,(-?\d+(?:\.\d+)?)\]"
    m = re.search(pat, html)
    if not m:
        return html, False
    grp_start, grp_end = m.start(1), m.end(1)
    return html[:grp_start] + repl + html[grp_end:], True


def replace_after_anchor(html: str, anchor: str, value_pattern: str, new_value) -> tuple[str, bool]:
    """Find `anchor` then replace the next `value_pattern` match with new_value."""
    if new_value is None:
        return html, False
    m = re.search(re.escape(anchor) + r"(.*?)" + value_pattern, html, re.DOTALL)
    if not m:
        return html, False
    pre = html[: m.start()]
    span_inner = html[m.start() : m.end()]
    # Replace just the captured value group within span_inner
    inner_match = re.search(value_pattern, span_inner)
    inner_full = inner_match.group(0)
    inner_replaced = re.sub(value_pattern, new_value, inner_full, count=1)
    span_inner = span_inner.replace(inner_full, inner_replaced, 1)
    return pre + span_inner + html[m.end() :], True


# ---------- LOAD FILES ----------

HAV = REPO / "haverhill-market-report.html"
MA = REPO / "ma-housing-dashboard.html"
MD = REPO / "MASTER_DATA.md"

hav = HAV.read_text(encoding="utf-8")
ma = MA.read_text(encoding="utf-8")
md = MD.read_text(encoding="utf-8")


# ---------- MA DASHBOARD: data arrays ----------

ma_changes = []

def _do(label: str, fn):
    """Run a substitution; record success/miss."""
    result = fn()
    if isinstance(result, tuple):
        new_html, ok = result
    else:
        new_html, ok = result, True
    ma_changes.append((label, ok))
    return new_html

# d.ma / d.boston / d.essex / d.nbpt — price, sqft, dom, units, supply
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
        ma = _do(
            f"ma-dash arr d.{ma_key}.{metric}",
            lambda v=ma, m=metric, k=ma_key, x=val: replace_array_tail(v, k, m, x, is_float=True),
        )

# MA dashboard: Overview cards (line ~465-468) — use anchor-based replacement
# MA card
ma_avg_full = _money_full(results["ma"]["sf"]["avg_price"])
ma_dom = results["ma"]["sf"]["avg_dom"]
ma_units = results["ma"]["sf"]["count"]
ma_supply = ms["ma"]
ma_sqft = round(results["ma"]["sf"]["avg_sqft"]) if results["ma"]["sf"]["avg_sqft"] else None

boston_val_k = _money_k(results["boston"]["sf"]["avg_price"])
boston_dom = results["boston"]["sf"]["avg_dom"]
boston_sqft = round(results["boston"]["sf"]["avg_sqft"]) if results["boston"]["sf"]["avg_sqft"] else None

essex_full = _money_full(results["essex"]["sf"]["avg_price"])
essex_dom = results["essex"]["sf"]["avg_dom"]
essex_sqft = round(results["essex"]["sf"]["avg_sqft"]) if results["essex"]["sf"]["avg_sqft"] else None

nbpt_val_k = _money_k(results["newburyport"]["sf"]["avg_price"])
nbpt_dom = results["newburyport"]["sf"]["avg_dom"]
nbpt_sqft = round(results["newburyport"]["sf"]["avg_sqft"]) if results["newburyport"]["sf"]["avg_sqft"] else None


def fmt_dom(d):
    return None if d is None else str(round(d))


# Overview cards — match by card-label anchor then replace the next card-val
def patch_overview_card(html, label, val_str, sqft, dom, units=None, supply=None):
    """Update the Overview card for `label` market."""
    # Find the <div class="card ..."><div class="card-label">LABEL</div><div class="card-val ...">$X</div>...</div>
    # Card is one HTML element with nested children. We anchor on the label.
    anchor = f'class="card-label">{label}</div>'
    idx = html.find(anchor)
    if idx < 0:
        return html, False
    # Find the closing </div> of this card. Easier: take a 1200-char window and substitute.
    end_idx = html.find('</div></div>', idx) + len('</div></div>')
    # Try to find the full card by walking divs — fallback: bounded window
    window_end = min(idx + 1500, len(html))
    window = html[idx:window_end]
    new_window = window
    # card-val
    if val_str:
        new_window = re.sub(
            r'(class="card-val[^"]*">)\$[\d.,KM]+(</div>)',
            lambda m, v=val_str: m.group(1) + v + m.group(2),
            new_window,
            count=1,
        )
    # card-metric-label "$/SqFt" -> next card-metric-val
    if sqft is not None:
        new_window = re.sub(
            r'(card-metric-label">\$/SqFt</div><div class="card-metric-val">)\$[\d.,]+',
            rf'\g<1>${sqft}',
            new_window,
            count=1,
        )
    # DOM
    if dom is not None:
        new_window = re.sub(
            r'(card-metric-label">(?:Days on Market|DOM)</div><div class="card-metric-val">)[\d.]+',
            rf'\g<1>{fmt_dom(dom)}',
            new_window,
            count=1,
        )
    # Units (12mo)
    if units is not None:
        new_window = re.sub(
            r'(card-metric-label">Units \(12mo\)</div><div class="card-metric-val">)[\d.,]+',
            rf'\g<1>{units:,}',
            new_window,
            count=1,
        )
    # Months Supply
    if supply is not None:
        new_window = re.sub(
            r'(card-metric-label">Months Supply</div><div class="card-metric-val">)[\d.,]+',
            rf'\g<1>{supply}',
            new_window,
            count=1,
        )
    return html[:idx] + new_window + html[window_end:], (new_window != window)


ma, ok = patch_overview_card(ma, "Massachusetts", ma_avg_full, ma_sqft, ma_dom, ma_units, ma_supply)
ma_changes.append(("ma-dash overview card MA", ok))
ma, ok = patch_overview_card(ma, "Boston", boston_val_k, boston_sqft, boston_dom)
ma_changes.append(("ma-dash overview card Boston", ok))
ma, ok = patch_overview_card(ma, "Essex County", essex_full, essex_sqft, essex_dom)
ma_changes.append(("ma-dash overview card Essex", ok))
ma, ok = patch_overview_card(ma, "Newburyport", nbpt_val_k, nbpt_sqft, nbpt_dom)
ma_changes.append(("ma-dash overview card Newburyport", ok))


# Property type cards (pt-ma-val etc. — line 533-536)
def patch_pt_card(html, id_, sf_avg, condo_avg, multi_avg):
    """Update the property-type breakdown card (id=pt-{market}-val)."""
    # The card has id="pt-X-val">$Y SF</div> followed by Condo/Multi card-metric-vals
    anchor = f'id="{id_}">'
    idx = html.find(anchor)
    if idx < 0:
        return html, False
    end_window = min(idx + 800, len(html))
    window = html[idx:end_window]
    new_window = window
    if sf_avg:
        new_window = re.sub(
            r'(>)\$[\d.,KM]+ SF(</div>)',
            rf'\g<1>{_money_k(sf_avg)} SF\g<2>',
            new_window,
            count=1,
        )
    if condo_avg is not None:
        new_window = re.sub(
            r'(card-metric-label">Condo 2026</div><div class="card-metric-val">)\$[\d.,KM]+',
            rf'\g<1>{_money_k(condo_avg)}',
            new_window,
            count=1,
        )
    if multi_avg is not None:
        new_window = re.sub(
            r'(card-metric-label">Multi 2026</div><div class="card-metric-val">)\$[\d.,KM]+',
            rf'\g<1>{_money_k(multi_avg)}',
            new_window,
            count=1,
        )
    return html[:idx] + new_window + html[end_window:], (new_window != window)


ma, ok = patch_pt_card(
    ma, "pt-ma-val",
    results["ma"]["sf"]["avg_price"],
    results["ma"]["co"]["avg_price"],
    results["ma"]["mf"]["avg_price"],
)
ma_changes.append(("ma-dash pt-ma card", ok))
ma, ok = patch_pt_card(
    ma, "pt-boston-val",
    results["boston"]["sf"]["avg_price"],
    results["boston"]["co"]["avg_price"],
    results["boston"]["mf"]["avg_price"],
)
ma_changes.append(("ma-dash pt-boston card", ok))
ma, ok = patch_pt_card(
    ma, "pt-essex-val",
    results["essex"]["sf"]["avg_price"],
    results["essex"]["co"]["avg_price"],
    results["essex"]["mf"]["avg_price"],
)
ma_changes.append(("ma-dash pt-essex card", ok))
ma, ok = patch_pt_card(
    ma, "pt-nbpt-val",
    results["newburyport"]["sf"]["avg_price"],
    results["newburyport"]["co"]["avg_price"],
    results["newburyport"]["mf"]["avg_price"],
)
ma_changes.append(("ma-dash pt-nbpt card", ok))


# MA hero stats (lines ~378-398)
hero_ma_k = _money_k(results["ma"]["sf"]["avg_price"])
hero_nbpt_full = (
    f"${results['newburyport']['sf']['avg_price']/1_000_000:.2f}M"
    if results["newburyport"]["sf"]["avg_price"]
    else None
)


def patch_ma_hero(html):
    out = html
    changes = 0
    # MA Average
    if hero_ma_k:
        out, n = re.subn(
            r'(<div class="hs-label">MA Average</div>\s*<div class="hs-val gold">)\$[\d.,KM]+(</div>)',
            rf'\g<1>{hero_ma_k}\g<2>',
            out,
            count=1,
        )
        changes += n
    # Newburyport
    if hero_nbpt_full:
        out, n = re.subn(
            r'(<div class="hs-label">Newburyport</div>\s*<div class="hs-val gold">)\$[\d.,KM]+(</div>)',
            rf'\g<1>{hero_nbpt_full}\g<2>',
            out,
            count=1,
        )
        changes += n
    # DOM
    if ma_dom is not None:
        out, n = re.subn(
            r'(<div class="hs-label">Days on Market</div>\s*<div class="hs-val">)[\d.]+(</div>)',
            rf'\g<1>{fmt_dom(ma_dom)}\g<2>',
            out,
            count=1,
        )
        changes += n
    return out, changes > 0


ma, ok = patch_ma_hero(ma)
ma_changes.append(("ma-dash hero stats", ok))


# Footer "Updated April 25, 2026"
footer_date = TODAY.strftime("%B %d, %Y")
ma, n = re.subn(
    r'(Updated )[A-Z][a-z]+ \d+, \d{4}',
    rf'\g<1>{footer_date}',
    ma,
    count=1,
)
ma_changes.append(("ma-dash footer date", n > 0))
ma, n = re.subn(
    r'(<div class="hero-date">)[A-Z][a-z]+ \d+, \d{4}',
    rf'\g<1>{footer_date}',
    ma,
    count=1,
)
ma_changes.append(("ma-dash hero date", n > 0))


# ---------- HAVERHILL DASHBOARD ----------

hav_changes = []

# Data arrays: sf, co, mf, es (Essex SF), ma (MA SF)
HAV_ARRS = [
    ("sf", "haverhill", "sf", [
        ("price", "avg_price", True),
        ("sqft", "avg_sqft", True),
        ("dom", "avg_dom", True),
        ("sold", "count", False),  # YTD count — see note below
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
        hav, ok = replace_array_tail(hav, var, arr_key, val, is_float=is_float)
        hav_changes.append((f"hav-dash arr {var}.{arr_key}", ok))

# Haverhill SF inv & supply arrays (special — only sf has inv/supply)
hav, ok = replace_array_tail(hav, "sf", "inv", active_sf["haverhill"], is_float=False)
hav_changes.append(("hav-dash arr sf.inv", ok))
hav, ok = replace_array_tail(hav, "sf", "supply", ms["haverhill"], is_float=True)
hav_changes.append(("hav-dash arr sf.supply", ok))


# Haverhill hero stats (lines ~157-162)
def patch_hav_hero(html):
    out = html
    pairs = [
        (r'(<div class="hs-l">SF Avg Sale</div><div class="hs-v blue">)\$[\d.,KM]+(</div>)',
         _money_k(results["haverhill"]["sf"]["avg_price"])),
        (r'(<div class="hs-l">Condo Avg</div><div class="hs-v green">)\$[\d.,KM]+(</div>)',
         _money_k(results["haverhill"]["co"]["avg_price"])),
        (r'(<div class="hs-l">Multi-Family</div><div class="hs-v orange">)\$[\d.,KM]+(</div>)',
         _money_k(results["haverhill"]["mf"]["avg_price"])),
        (r'(<div class="hs-l">SF DOM</div><div class="hs-v">)[\d.]+(</div>)',
         fmt_dom(results["haverhill"]["sf"]["avg_dom"])),
        (r'(<div class="hs-l">SF Supply</div><div class="hs-v">)[\d.]+(</div>)',
         f"{ms['haverhill']}" if ms["haverhill"] is not None else None),
        (r'(<div class="hs-l">MA Statewide</div><div class="hs-v red">)\$[\d.,KM]+(</div>)',
         _money_k(results["ma"]["sf"]["avg_price"])),
    ]
    ok_any = False
    for pat, val in pairs:
        if val is None:
            continue
        new, n = re.subn(pat, rf"\g<1>{val}\g<2>", out, count=1)
        if n > 0:
            ok_any = True
            out = new
    return out, ok_any


hav, ok = patch_hav_hero(hav)
hav_changes.append(("hav-dash hero stats", ok))


# Haverhill panel snapshot cards (SF/Condo/MF)
def patch_hav_snapshot(html, panel_id, price_val, sqft, dom, supply_or_sold, supply_label):
    """Update the 4 cards at top of each Haverhill panel (SF, Condo, MF)."""
    start = html.find(f'id="p-{panel_id}"')
    if start < 0:
        return html, False
    # Take a 2500-char window — panel snapshot cards are in the first ~1500 chars after id
    end = min(start + 2500, len(html))
    window = html[start:end]
    new_window = window
    if price_val is not None:
        new_window = re.sub(
            r'(Avg Sale Price</div><div class="cv [a-z]+">)\$[\d.,]+',
            rf"\g<1>{_money_full(price_val)}",
            new_window,
            count=1,
        )
    if sqft is not None:
        new_window = re.sub(
            r'(\$/SqFt</div><div class="cv [a-z]+">)\$[\d.,]+',
            rf"\g<1>${round(sqft)}",
            new_window,
            count=1,
        )
    if dom is not None:
        new_window = re.sub(
            r'(Days on Market</div><div class="cv [a-z]+">)[\d.]+',
            rf"\g<1>{fmt_dom(dom)}",
            new_window,
            count=1,
        )
    if supply_or_sold is not None:
        new_window = re.sub(
            rf'({re.escape(supply_label)}</div><div class="cv [a-z]+">)[\d.,]+',
            rf"\g<1>{supply_or_sold}",
            new_window,
            count=1,
        )
    return html[:start] + new_window + html[end:], (new_window != window)


# SF panel: Avg, $/SqFt, DOM, Months Supply (4th card)
hav, ok = patch_hav_snapshot(
    hav, "sf",
    results["haverhill"]["sf"]["avg_price"],
    results["haverhill"]["sf"]["avg_sqft"],
    results["haverhill"]["sf"]["avg_dom"],
    ms["haverhill"],
    "Months Supply",
)
hav_changes.append(("hav-dash SF snapshot", ok))

# Condo panel: Avg, $/SqFt, DOM, Months Supply
hav, ok = patch_hav_snapshot(
    hav, "condo",
    results["haverhill"]["co"]["avg_price"],
    results["haverhill"]["co"]["avg_sqft"],
    results["haverhill"]["co"]["avg_dom"],
    ms_hav_co,
    "Months Supply",
)
hav_changes.append(("hav-dash Condo snapshot", ok))

# MF panel: Avg, $/SqFt, DOM, 12mo Sold (4th card label is "12mo Sold")
hav, ok = patch_hav_snapshot(
    hav, "mf",
    results["haverhill"]["mf"]["avg_price"],
    results["haverhill"]["mf"]["avg_sqft"],
    results["haverhill"]["mf"]["avg_dom"],
    results["haverhill"]["mf"]["count"],
    "12mo Sold",
)
hav_changes.append(("hav-dash MF snapshot", ok))


# Footer prepared date
hav, n = re.subn(
    r'(Prepared )[A-Z][a-z]+ \d+, \d{4}',
    rf"\g<1>{footer_date}",
    hav,
    count=1,
)
hav_changes.append(("hav-dash footer date", n > 0))
hav, n = re.subn(
    r'(<div class="hero-date">)[A-Z][a-z]+ \d+, \d{4}',
    rf"\g<1>{footer_date}",
    hav,
    count=1,
)
hav_changes.append(("hav-dash hero date", n > 0))


# ---------- MASTER_DATA.md ----------

md_changes = []

def md_replace(text, pattern, repl, label):
    new_text, n = re.subn(pattern, repl, text, count=1)
    md_changes.append((label, n > 0))
    return new_text


# MA statewide avg price (current year row in the 5-year table)
md = md_replace(
    md,
    rf"(\| {YEAR} \| )\$[\d,]+( \| \$[\d,]+ \| \$[\d,]+ \| \$[\d,]+ \|)",
    rf"\g<1>{_money_full(results['ma']['sf']['avg_price'])}\g<2>",
    f"MASTER_DATA MA {YEAR} avg",
)

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

# MA Units Sold (YTD count)
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


# ---------- REPORT ----------

print("\n[mls-update] Substitution report:")
for label, ok in ma_changes + hav_changes + md_changes:
    marker = "OK" if ok else "MISS"
    print(f"  [{marker:>4}] {label}")

misses = sum(1 for _, ok in ma_changes + hav_changes + md_changes if not ok)
if misses:
    print(f"\n[mls-update] {misses} substitutions missed (no pattern match). "
          "Check dashboard HTML for format drift.")

print("\n[mls-update] Done.")
