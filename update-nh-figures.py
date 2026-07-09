#!/usr/bin/env python3
"""
Build data/nh-figures.json from PrimeMLS for the NH housing report.

Markets: NH statewide + Portsmouth, Salem, Derry, Windham. Single-family
residential, closed since 2020, plus current active inventory.

Design (see README.md for why):
  * Sold filter uses the STRING status: StandardStatus eq 'Closed'.
  * NEVER uses $count (it 500s) - paginates and counts client-side.
  * Statewide is month-windowed to keep result sets small and $skip shallow.
  * DAILY-CRON FRIENDLY: past statewide months are cached under data/_raw_nh/;
    the current + previous month, all towns, and active inventory are always
    re-fetched. Persist data/_raw_nh/ between CI runs (actions/cache) so a daily
    run only re-pulls recent data, not 90k historical records.
  * LICENSING: data/_raw_nh/ holds record-level MLS data and MUST NOT be
    committed/published. Only the aggregated data/nh-figures.json is published.

Usage:
  python update-nh-figures.py cities   # 4 towns + active (fast)
  python update-nh-figures.py state    # NH statewide (recent months + cache)
  python update-nh-figures.py all      # everything
"""
import datetime
import json
import statistics
import sys
from pathlib import Path

from primemls import fetch_all

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "_raw_nh"           # record-level cache — NEVER commit/publish
RAW.mkdir(parents=True, exist_ok=True)
OUT = HERE / "data" / "nh-figures.json"   # aggregates only — safe to publish

START_YEAR = 2020
TODAY = datetime.date.today()
SELECT = "ListingId,ClosePrice,ListPrice,CloseDate,DaysOnMarket,BedroomsTotal,LivingArea,City"
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
    ("$1.5-2M", 1_500_000, 2_000_000), ("$2M+", 2_000_000, 10**12),
]


def _cache(name, thunk, force=False):
    f = RAW / f"{name}.json"
    if f.exists() and not force:
        return json.loads(f.read_text())
    rows = thunk()
    f.write_text(json.dumps(rows))
    return rows


def _recent(y, m):
    """Current + previous month are never final (late-recorded sales) -> always re-fetch."""
    return (y * 12 + m) >= (TODAY.year * 12 + TODAY.month) - 1


def pull_state():
    rows = []
    y, m = START_YEAR, 1
    while (y, m) <= (TODAY.year, TODAY.month):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        win = _cache(
            f"closed_NH_{y}-{m:02d}",
            lambda y=y, m=m, ny=ny, nm=nm: fetch_all(
                f"{SF} and StateOrProvince eq 'NH' "
                f"and CloseDate ge {y}-{m:02d}-01 and CloseDate lt {ny}-{nm:02d}-01",
                SELECT, pace=0.5),
            force=_recent(y, m),
        )
        rows += win
        print(f"    {y}-{m:02d}: {len(win)} sold (running {len(rows)})")
        y, m = ny, nm
    return rows


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
        cd, price = r.get("CloseDate"), r.get("ClosePrice")
        if cd and price:
            yearly.setdefault(cd[:4], []).append(price)

    dist = [{"band": lbl, "count": sum(1 for p in cp if lo <= p < hi)} for lbl, lo, hi in DIST_BANDS]
    act_list = [r["ListPrice"] for r in active if r.get("ListPrice")]
    return {
        "volume": len(cp),
        "median_sale": round(statistics.median(cp)),
        "avg_sale": round(statistics.mean(cp)),
        "avg_dom": round(statistics.mean(dom)) if dom else None,
        "splp_pct": round(sum(c for c, _ in pairs) / sum(l for _, l in pairs) * 100, 2) if pairs else None,
        "active_count": len(active),
        "active_avg_list": round(statistics.mean(act_list)) if act_list else None,
        "active_median_list": round(statistics.median(act_list)) if act_list else None,
        "by_bedroom": {k: {"avg": round(statistics.mean(v)), "n": len(v)} for k, v in sorted(beds.items())},
        "by_year": {y: {"n": len(v), "median": round(statistics.median(v)), "avg": round(statistics.mean(v))}
                    for y, v in sorted(yearly.items())},
        "distribution": dist,
    }


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


def do_cities(data):
    for city in CITIES:
        print(f"[{city}] pulling sold + active (fresh) ...")
        sold = fetch_all(f"{SF} and City eq '{city}' and CloseDate ge {START_YEAR}-01-01", SELECT)
        active = fetch_all(f"{ACT} and City eq '{city}'", "ListingId,ListPrice,BedroomsTotal", order=None)
        data["markets"][city] = aggregate(sold, active)
        print(f"  {city}: {data['markets'][city]['volume']} sold, median ${data['markets'][city]['median_sale']:,}")
        write_out(data)


def do_state(data):
    print("[NH Statewide] pulling sold (month-windowed; recent months fresh) ...")
    sold = pull_state()
    active = fetch_all(f"{ACT} and StateOrProvince eq 'NH'", "ListingId,ListPrice,BedroomsTotal", order=None)
    data["markets"]["NH Statewide"] = aggregate(sold, active)
    m = data["markets"]["NH Statewide"]
    print(f"  NH Statewide: {m['volume']} sold, median ${m['median_sale']:,}")
    write_out(data)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    data = load_out()
    if mode in ("cities", "all"):
        do_cities(data)
    if mode in ("state", "all"):
        do_state(data)
    print("done:", mode)
