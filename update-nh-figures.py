#!/usr/bin/env python3
"""
Build data/nh-figures.json from PrimeMLS for the NH housing report.

Markets: NH statewide + Portsmouth, Salem, Derry, Windham. Single-family
residential, closed since 2020, plus current active inventory.

LOW-VOLUME DAILY DESIGN (see README): statewide history lives in
data/nh-state-monthly.json as committed monthly sufficient-statistics
(sums/counts + a $5k price histogram — derived, license-safe). Each run
re-pulls only the current+previous month statewide, the 4 towns, and active,
then reconstructs statewide from the histogram.

SAFE-WRITE: every market is validated (never None/empty; volume can't drop vs
the last published figures — sold counts only grow). If ANY market fails the
check the run ABORTS and writes nothing, so a truncated / rate-limited pull can
never overwrite good data. Meant to run on a residential IP (PrimeMLS/Cloudflare
throttles datacenter/CI IPs and returns truncated results).

Usage: seed | cities | state | all
"""
import datetime
import glob
import json
import statistics
import sys
from pathlib import Path

from primemls import fetch_all

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "_raw_nh"                       # raw records — gitignored, NEVER published
RAW.mkdir(parents=True, exist_ok=True)
OUT = HERE / "data" / "nh-figures.json"               # report aggregates — published
MONTHLY = HERE / "data" / "nh-state-monthly.json"     # statewide monthly sufficient-stats — published (derived)

START_YEAR = 2020
TODAY = datetime.date.today()
BIN = 5000
SELECT = "ListingId,ClosePrice,ListPrice,CloseDate,DaysOnMarket,BedroomsTotal,City"
SF = ("StandardStatus eq 'Closed' and PropertyType eq 'Residential' "
      "and PropertySubType eq 'Single Family Residence'")
ACT = ("StandardStatus eq 'Active' and PropertyType eq 'Residential' "
       "and PropertySubType eq 'Single Family Residence'")
CITIES = ["Portsmouth", "Salem", "Derry", "Windham"]
DIST_BANDS = [
    ("<$200K", 0, 200_000), ("$200-300K", 200_000, 300_000), ("$300-400K", 300_000, 400_000),
    ("$400-500K", 400_000, 500_000), ("$500-600K", 500_000, 600_000), ("$600-700K", 600_000, 700_000),
    ("$700-800K", 700_000, 800_000), ("$800-900K", 800_000, 900_000), ("$900K-1M", 900_000, 1_000_000),
    ("$1-1.25M", 1_000_000, 1_250_000), ("$1.25-1.5M", 1_250_000, 1_500_000),
    ("$1.5-2M", 1_500_000, 2_000_000), ("$2M+", 2_000_000, 10 ** 12),
]


# ---- statewide monthly sufficient statistics ------------------------------
def month_stats(rows):
    cp = [r["ClosePrice"] for r in rows if r.get("ClosePrice")]
    pairs = [(r["ClosePrice"], r["ListPrice"]) for r in rows if r.get("ClosePrice") and r.get("ListPrice")]
    dom = [r["DaysOnMarket"] for r in rows if isinstance(r.get("DaysOnMarket"), (int, float)) and 0 <= r["DaysOnMarket"] < 3000]
    beds = {}
    for r in rows:
        b = r.get("BedroomsTotal")
        if r.get("ClosePrice") and isinstance(b, int) and b > 0:
            e = beds.setdefault("5+" if b >= 5 else str(b), [0, 0])
            e[0] += r["ClosePrice"]; e[1] += 1
    hist = {}
    for p in cp:
        k = str(int(p // BIN) * BIN)
        hist[k] = hist.get(k, 0) + 1
    return {"count": len(cp), "sum_cp": sum(cp),
            "sum_cp_pair": sum(c for c, _ in pairs), "sum_lp_pair": sum(l for _, l in pairs),
            "dom_sum": sum(dom), "dom_count": len(dom),
            "beds": {k: {"sum": v[0], "n": v[1]} for k, v in beds.items()}, "hist": hist}


def _median_from_hist(hist):
    total = sum(hist.values())
    if not total:
        return None
    target, cum = total / 2, 0
    for lo in sorted(hist, key=int):
        c = hist[lo]
        if cum + c >= target:
            return round(int(lo) + (target - cum) / c * BIN)
        cum += c
    return int(lo)


def _combine(month_list):
    agg = {"count": 0, "sum_cp": 0, "sum_cp_pair": 0, "sum_lp_pair": 0, "dom_sum": 0, "dom_count": 0}
    beds, hist = {}, {}
    for m in month_list:
        for k in agg:
            agg[k] += m[k]
        for k, v in m["beds"].items():
            e = beds.setdefault(k, [0, 0]); e[0] += v["sum"]; e[1] += v["n"]
        for lo, c in m["hist"].items():
            hist[lo] = hist.get(lo, 0) + c
    return agg, beds, hist


def statewide_from_monthly(monthly, active):
    agg, beds, hist = _combine(list(monthly.values()))
    if not agg["count"]:
        return None
    by_year = {}
    for ym, m in monthly.items():
        by_year.setdefault(ym[:4], []).append(m)
    by_year_out = {}
    for y, ms in sorted(by_year.items()):
        ya, _, yh = _combine(ms)
        by_year_out[y] = {"n": ya["count"], "median": _median_from_hist(yh),
                          "avg": round(ya["sum_cp"] / max(1, ya["count"]))}
    act_list = [r["ListPrice"] for r in active if r.get("ListPrice")]
    return {
        "volume": agg["count"], "median_sale": _median_from_hist(hist),
        "avg_sale": round(agg["sum_cp"] / agg["count"]),
        "avg_dom": round(agg["dom_sum"] / agg["dom_count"]) if agg["dom_count"] else None,
        "splp_pct": round(agg["sum_cp_pair"] / agg["sum_lp_pair"] * 100, 2) if agg["sum_lp_pair"] else None,
        "active_count": len(active),
        "active_avg_list": round(statistics.mean(act_list)) if act_list else None,
        "active_median_list": round(statistics.median(act_list)) if act_list else None,
        "by_bedroom": {k: {"avg": round(v[0] / v[1]), "n": v[1]} for k, v in sorted(beds.items())},
        "by_year": by_year_out,
        "distribution": [{"band": lbl, "count": sum(c for lo, c in hist.items() if l <= int(lo) < h)}
                         for lbl, l, h in DIST_BANDS],
    }


# ---- towns (pulled fresh each run) ----------------------------------------
def aggregate(sold, active):
    cp = [r["ClosePrice"] for r in sold if r.get("ClosePrice")]
    if not cp:
        return None
    pairs = [(r["ClosePrice"], r["ListPrice"]) for r in sold if r.get("ClosePrice") and r.get("ListPrice")]
    dom = [r["DaysOnMarket"] for r in sold if isinstance(r.get("DaysOnMarket"), (int, float)) and 0 <= r["DaysOnMarket"] < 3000]
    beds = {}
    for r in sold:
        b = r.get("BedroomsTotal")
        if r.get("ClosePrice") and isinstance(b, int) and b > 0:
            beds.setdefault("5+" if b >= 5 else str(b), []).append(r["ClosePrice"])
    yearly = {}
    for r in sold:
        if r.get("CloseDate") and r.get("ClosePrice"):
            yearly.setdefault(r["CloseDate"][:4], []).append(r["ClosePrice"])
    act_list = [r["ListPrice"] for r in active if r.get("ListPrice")]
    return {
        "volume": len(cp), "median_sale": round(statistics.median(cp)), "avg_sale": round(statistics.mean(cp)),
        "avg_dom": round(statistics.mean(dom)) if dom else None,
        "splp_pct": round(sum(c for c, _ in pairs) / sum(l for _, l in pairs) * 100, 2) if pairs else None,
        "active_count": len(active),
        "active_avg_list": round(statistics.mean(act_list)) if act_list else None,
        "active_median_list": round(statistics.median(act_list)) if act_list else None,
        "by_bedroom": {k: {"avg": round(statistics.mean(v)), "n": len(v)} for k, v in sorted(beds.items())},
        "by_year": {y: {"n": len(v), "median": round(statistics.median(v)), "avg": round(statistics.mean(v))}
                    for y, v in sorted(yearly.items())},
        "distribution": [{"band": lbl, "count": sum(1 for p in cp if lo <= p < hi)} for lbl, lo, hi in DIST_BANDS],
    }


# ---- safety check ----------------------------------------------------------
# Exit code for "the pull was throttled/truncated, nothing was written". This is
# an expected, self-healing condition — the next run fixes it — so callers can
# treat it as a neutral skip rather than a build failure. Distinct from 1, which
# means a genuine error worth looking at. (75 = BSD sysexits EX_TEMPFAIL.)
EXIT_THROTTLED = 75


def _abort_throttled(msg):
    print(f"ABORT: {msg} — nothing written.", file=sys.stderr)
    raise SystemExit(EXIT_THROTTLED)


def _check(name, entry, prior):
    """Abort the whole run if a market looks truncated (empty, or volume dropped
    vs the last published figures — sold counts only ever grow)."""
    if not entry or not entry.get("volume"):
        _abort_throttled(f"'{name}' returned no data (truncated / rate-limited pull)")
    pv = (prior.get("markets", {}).get(name) or {}).get("volume")
    # Closed sales are cumulative, so any real decrease is a truncated pull rather
    # than a market move. The old 2% band was wide enough to let a mild truncation
    # through and publish it as real (e.g. 1,740 of 1,755 passed). 0.5% still
    # tolerates the odd retroactively-corrected listing.
    if pv and entry["volume"] < pv * 0.995:
        _abort_throttled(f"'{name}' volume {entry['volume']} < previous {pv} (truncated pull)")


# ---- io + drivers ----------------------------------------------------------
def load_out():
    if OUT.exists():
        return json.loads(OUT.read_text())
    return {"source": "PrimeMLS", "compiled_by": "Duncan Burns",
            "attribution": "Data compiled by Duncan Burns · Source: PrimeMLS",
            "property_type": "Single Family Residential", "since": f"{START_YEAR}-01-01", "markets": {}}


def write_out(data):
    data["updated"] = TODAY.isoformat()
    OUT.write_text(json.dumps(data, indent=2))
    print(f"  wrote {OUT} ({len(data['markets'])} markets)")


def _months():
    y, m = START_YEAR, 1
    while (y, m) <= (TODAY.year, TODAY.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def do_cities(data, prior):
    for city in CITIES:
        print(f"[{city}] pulling sold + active ...")
        sold = fetch_all(f"{SF} and City eq '{city}' and CloseDate ge {START_YEAR}-01-01", SELECT)
        active = fetch_all(f"{ACT} and City eq '{city}'", "ListingId,ListPrice,BedroomsTotal", order=None)
        entry = aggregate(sold, active)
        _check(city, entry, prior)
        data["markets"][city] = entry
        print(f"  {city}: {entry['volume']} sold, median ${entry['median_sale']:,}")


def do_state(data, prior):
    """Returns the updated monthly dict; the CALLER persists it only after full success."""
    monthly = json.loads(MONTHLY.read_text()) if MONTHLY.exists() else {}
    cur = TODAY.year * 12 + TODAY.month
    for y, m in _months():
        ym = f"{y}-{m:02d}"
        if ym in monthly and (y * 12 + m) < cur - 1:
            continue
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        rows = fetch_all(f"{SF} and StateOrProvince eq 'NH' and CloseDate ge {y}-{m:02d}-01 "
                         f"and CloseDate lt {ny}-{nm:02d}-01", SELECT, pace=0.6)
        monthly[ym] = month_stats(rows)
        print(f"    {ym}: {monthly[ym]['count']} sold (fresh)")
    active = fetch_all(f"{ACT} and StateOrProvince eq 'NH'", "ListingId,ListPrice,BedroomsTotal", order=None)
    entry = statewide_from_monthly(monthly, active)
    _check("NH Statewide", entry, prior)
    data["markets"]["NH Statewide"] = entry
    print(f"  NH Statewide: {entry['volume']} sold, median ${entry['median_sale']:,}")
    return monthly


def do_seed():
    """Build nh-state-monthly.json from the local data/_raw_nh/closed_NH_*.json cache (no API)."""
    monthly = {}
    for f in sorted(glob.glob(str(RAW / "closed_NH_*.json"))):
        ym = Path(f).stem.replace("closed_NH_", "")
        monthly[ym] = month_stats(json.loads(Path(f).read_text()))
        print(f"  {ym}: {monthly[ym]['count']}")
    MONTHLY.write_text(json.dumps(monthly))
    print(f"  wrote {MONTHLY} ({len(monthly)} months)")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "seed":
        do_seed()
        print("done: seed")
        sys.exit(0)
    prior = load_out()
    data = load_out()
    monthly = None
    if mode in ("cities", "all"):
        do_cities(data, prior)
    if mode in ("state", "all"):
        monthly = do_state(data, prior)
    # Every market validated -> persist atomically (nothing written before here).
    if monthly is not None:
        MONTHLY.write_text(json.dumps(monthly))
    write_out(data)
    print("done:", mode)
