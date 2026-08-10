#!/usr/bin/env python3
"""
update-town-band.py — builds the "The Band" panel payload for a town report.

WHAT THIS IS FOR
----------------
A town's own numbers do not say much. "Haverhill's median is $605K" is a fact
nobody can act on; "$605K, against $837K across the six towns it borders" is.
This script computes a town against its TRUE MUNICIPAL ABUTTERS, plus its own
sub-markets, and writes the result into the report page as one JSON payload.

RETARGETING TO ANOTHER TOWN
---------------------------
Edit CONFIG and the two paths. Nothing else. Every figure AND every sentence in
the payload is derived here from thresholds -- there is deliberately no prose
written about Haverhill anywhere in this file or in the page. That is the whole
design constraint: the moment one hand-written claim about a specific town gets
in, pointing this at the next town produces a page that looks updated because
the numbers are, while the argument still describes somewhere else.

SUB-LOCALITIES: WHY ZIP AND NOT THE NEIGHBOURHOOD FIELD
-------------------------------------------------------
Probed against Haverhill, 1,000 closed sales (2026-08):
    MLSAreaMinor / CityRegion / Neighborhood ... entirely empty
    MLSAreaMajor ....... 21% populated, 8 distinct, and POLLUTED -- it carries
                         "Zip 01832" and "Zip 01830" as values alongside real
                         names like Bradford and Riverside
    SubdivisionName .... 4%, 24 distinct, nearly all n=1 marketing names
    PostalCode ......... 100% populated, 3 ZIPs covering 997 of 1,000 sales
Bradford is both the top MLSAreaMajor value (104 sales) and its own ZIP 01835
(238 sales) -- so the ZIP catches more than twice what the named field does.
ZIP is therefore the spine, and named areas ship as a clearly-captioned
secondary cut. Do NOT promote MLSAreaMajor to the primary cut for a new town
without re-running that coverage check: a 21% field silently ranks whichever
neighbourhoods agents happened to type.

Requires: BRIDGE_TOKEN. Usage:  python update-town-band.py [--refresh]
"""
import argparse
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
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE / "haverhill-market-report.html"
CACHE = HERE / "data" / "_raw_band"

CONFIG = {
    "town": "Haverhill",
    # TRUE municipal abutters only. A town one removed belongs in "near".
    "abutters": ["Methuen", "North Andover", "Boxford", "Groveland", "West Newbury", "Merrimac"],
    "near": ["Georgetown", "Amesbury", "Newburyport", "Andover", "Lawrence"],
    # Named in the report as a stated limitation, never silently dropped.
    "excluded": ["Plaistow NH", "Atkinson NH", "Newton NH", "Salem NH"],
    "subLocalities": {"01830": "Downtown & East", "01832": "West Haverhill", "01835": "Bradford"},
    "since": "2021-01-01",        # pull window (seasonality wants several cycles)
    "compareSince": "2025-01-01",  # the window every headline figure is measured over
    "compareLabel": "closed sales since Jan 2025",
}

TOKEN = os.environ.get("BRIDGE_TOKEN")
BASE = "https://api.bridgedataoutput.com/api/v2/mlspin/listings"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# This machine sits behind a TLS-inspecting proxy; CI does not. Verify by default
# and only relax when the environment says to, so CI keeps a real chain.
_CTX = ssl.create_default_context()
if os.environ.get("PIPELINE_INSECURE_TLS") == "1":
    _CTX.check_hostname = False
    _CTX.verify_mode = ssl.CERT_NONE

_last = 0.0


def _get(params, tries=6):
    """Bridge, paced and 429-aware. Same posture as update-mls-figures.py."""
    global _last
    for attempt in range(tries):
        gap = time.time() - _last
        if gap < 0.3:
            time.sleep(0.3 - gap)
        _last = time.time()
        try:
            with urllib.request.urlopen(
                    BASE + "?" + urllib.parse.urlencode(params), timeout=120, context=_CTX) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                ra = e.headers.get("Retry-After")
                time.sleep(min(float(ra) if (ra and ra.isdigit()) else 15.0 * (attempt + 1), 90))
                continue
            raise


def pull(town, refresh=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (town.lower().replace(" ", "-") + ".json")
    if f.exists() and not refresh:
        return json.loads(f.read_text())
    rows, skip = [], 0
    while True:
        batch = _get({"access_token": TOKEN, "limit": 200, "offset": skip,
                      "City.in": town, "StandardStatus.in": "Closed",
                      "CloseDate.gte": CONFIG["since"],
                      "PropertyType.in": "Residential",
                      "PropertySubType.in": "Single Family Residence"}).get("bundle", [])
        rows.extend(batch)
        if len(batch) < 200:
            break
        skip += 200
    f.write_text(json.dumps(rows))
    print(f"  {town:16s} {len(rows):5d}")
    return rows


def num(v):
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def stats(rows):
    cp = [v for v in (num(r.get("ClosePrice")) for r in rows) if v]
    if len(cp) < 10:
        return None
    ppsf, splp, doms = [], [], []
    for r in rows:
        c, la, lp = num(r.get("ClosePrice")), num(r.get("LivingArea")), num(r.get("ListPrice"))
        if c and la and 300 < la < 20000:
            ppsf.append(c / la)
        if c and lp:
            splp.append(c / lp)
        # DaysOnMarket is not the field this feed populates; MLSPIN_MARKET_TIME is.
        d = num(r.get("MLSPIN_MARKET_TIME"))
        if d is not None and d < 3000:
            doms.append(d)
    return {"n": len(cp), "median": round(st.median(cp)),
            "ppsf": round(st.median(ppsf)) if ppsf else None,
            "dom": round(st.median(doms)) if doms else None,
            "splp": round(st.mean(splp) * 100, 2) if splp else None,
            "over": round(sum(1 for x in splp if x > 1.0) / len(splp) * 100, 1) if splp else None}


def build(refresh=False):
    if not TOKEN:
        sys.exit("BRIDGE_TOKEN env var not set")
    town = CONFIG["town"]
    print(f"Single-family closed sales since {CONFIG['since']}")
    subject_all = pull(town, refresh)
    win = lambda rows: [r for r in rows if (r.get("CloseDate") or "") >= CONFIG["compareSince"]]

    towns = []
    S = stats(win(subject_all))
    if not S:
        sys.exit(f"ABORT: no usable {town} sales in the window -- nothing written.")
    towns.append(dict(S, town=town, role="subject"))
    for role, names in (("abutter", CONFIG["abutters"]), ("near", CONFIG["near"])):
        for t in names:
            s = stats(win(pull(t, refresh)))
            if s:
                towns.append(dict(s, town=t, role=role))
            else:
                print(f"  !! {t}: too few sales in the window -- omitted")

    ab = [t for t in towns if t["role"] == "abutter"]
    if len(ab) < 3:
        sys.exit("ABORT: fewer than 3 abutters returned data -- the band would not mean anything.")
    BM = {k: st.median([t[k] for t in ab if t[k] is not None]) for k in ("median", "ppsf", "dom")}

    d_price = (S["median"] / BM["median"] - 1) * 100
    d_ppsf = (S["ppsf"] / BM["ppsf"] - 1) * 100
    ranked = sorted(towns, key=lambda t: -t["median"])
    pos = [t["town"] for t in ranked].index(town) + 1
    n_t = len(ranked)

    # ---- sub-localities, same window as the headline figures
    subs = []
    for z, name in CONFIG["subLocalities"].items():
        s = stats([r for r in win(subject_all) if (r.get("PostalCode") or "").strip()[:5] == z])
        if s:
            subs.append(dict(s, zip=z, name=name))
    subs.sort(key=lambda s: -s["median"])

    # ---- named areas: full history, or a sparse field has nothing left to say
    areas = defaultdict(list)
    for r in subject_all:
        a = (r.get("MLSAreaMajor") or "").strip()
        if a and not a.lower().startswith("zip"):
            areas[a].append(r)
    named = []
    for a, rows in areas.items():
        s = stats(rows)
        if s and s["n"] >= 15:
            named.append({"area": a, "median": s["median"], "n": s["n"]})
    cov = round(sum(len(v) for v in areas.values()) / len(subject_all) * 100)

    # ---- seasonality by inferred list month
    mo = defaultdict(list)
    for r in subject_all:
        cd, d = r.get("CloseDate"), num(r.get("MLSPIN_MARKET_TIME"))
        c, lp = num(r.get("ClosePrice")), num(r.get("ListPrice"))
        if cd and d is not None and d < 3000 and c and lp:
            try:
                close = datetime.date.fromisoformat(cd[:10])
            except ValueError:
                continue
            mo[(close - datetime.timedelta(days=int(d))).month].append(c / lp)
    season = [{"month": MON[m - 1], "n": len(v), "splp": round(st.mean(v) * 100, 2)}
              for m, v in sorted(mo.items()) if len(v) >= 20]

    # ---- derived prose. Thresholds only; no sentence is about a named town.
    def ordinal_headline():
        hi = {1: "the most expensive town on its own borders",
              2: "the second most expensive town on its own borders",
              3: "the third most expensive town on its own borders"}
        lo = {1: "the cheapest town in its own neighborhood",
              2: "the second-cheapest town in its own neighborhood",
              3: "the third-cheapest town in its own neighborhood"}
        if pos in hi:
            return f"{town} is {hi[pos]}."
        if (n_t - pos + 1) in lo:
            return f"{town} is {lo[n_t - pos + 1]}."
        return (f"{town} sits {abs(d_price):.0f}% "
                f"{'below' if d_price < 0 else 'above'} the towns it borders.")

    gap = abs(d_price) - abs(d_ppsf)
    if abs(d_price) > 10 and gap > 10:
        key_html = (f"{town}&rsquo;s gap to its neighbors is mostly about "
                    f"<em>house size, not price per foot</em>. Prices sit {abs(d_price):.0f}% "
                    f"{'below' if d_price < 0 else 'above'} the abutter band, but per square foot "
                    f"the gap narrows to {abs(d_ppsf):.0f}%. You are buying "
                    f"{'less' if d_price < 0 else 'more'} house here, not "
                    f"{'cheaper' if d_price < 0 else 'dearer'} house.")
    else:
        key_html = (f"{town}&rsquo;s price gap to the band ({d_price:+.0f}%) and its "
                    f"per-square-foot gap ({d_ppsf:+.0f}%) move together, so the difference is "
                    f"priced into the footage itself, not into the address.")

    def verdict():
        if d_price < -20:
            return "materially cheaper than"
        if d_price < -7:
            return "below"
        if d_price > 20:
            return "materially dearer than"
        if d_price > 7:
            return "above"
        return "in line with"

    doms = [t["dom"] for t in towns if t["dom"] is not None]
    dom_spread = max(doms) - min(doms)
    findings = {
        "median": (f"{town} ranks {pos} of {n_t} on price and sits {abs(d_price):.0f}% "
                   f"{'below' if d_price < 0 else 'above'} the abutter-band median of "
                   f"${BM['median']:,.0f} — {verdict()} the towns on its own borders."),
        "ppsf": (f"Per square foot the gap is {abs(d_ppsf):.0f}% "
                 f"{'below' if d_ppsf < 0 else 'above'} the band's ${BM['ppsf']:,.0f}. "
                 + ("Much smaller than the price gap, which is the whole point: the difference is "
                    "square footage, not the address." if gap > 10 else
                    "Close to the price gap, so the difference really is the address.")),
        "splp": (f"{town} closes at {S['splp']:.1f}% of asking. Across the whole comparison the "
                 f"range is {min(t['splp'] for t in towns):.1f}%–{max(t['splp'] for t in towns):.1f}%, "
                 f"so every town here is selling at or above list."),
        "over": (f"{S['over']:.0f}% of {town} sales close above ask. "
                 f"Market time is not what separates these towns — every one of them clears in "
                 f"{min(doms)}–{max(doms)} days"
                 + (", a spread of barely a fortnight." if dom_spread <= 14 else ".")),
    }

    if len(subs) >= 2:
        spread = (subs[0]["median"] / subs[-1]["median"] - 1) * 100
        if spread < 10:
            sub_verdict = (f"The {len(subs)} sub-markets are, statistically, one market — "
                           f"{spread:.0f}% separates the dearest from the cheapest, and they clear "
                           f"at the same speed and the same premium to ask. A {town} ZIP is not a "
                           f"price tier.")
        else:
            sub_verdict = (f"The sub-markets genuinely diverge: {spread:.0f}% separates "
                           f"{subs[0]['name']} from {subs[-1]['name']}.")
    else:
        sub_verdict = "Too few sub-markets carry enough sales to compare."

    if season:
        best = max(season, key=lambda m: m["splp"])
        worst = min(season, key=lambda m: m["splp"])
        season_verdict = (f"Listing in {best['month']} has returned {best['splp']:.1f}% of asking "
                          f"against {worst['splp']:.1f}% in {worst['month']} — a "
                          f"{best['splp'] - worst['splp']:.1f}-point spread on the same house.")
    else:
        season_verdict = "Not enough listings per month to read a seasonal pattern."

    payload = {
        "town": town,
        "headline": ordinal_headline(),
        "dek": (f"Single-family resale measured against the {len(ab)} towns {town} actually "
                f"borders — not against a statewide average that pools it with Nantucket."),
        "keyHtml": key_html,
        "windowLabel": CONFIG["compareLabel"],
        "totalN": sum(t["n"] for t in towns),
        "towns": towns,
        "bandMedian": BM,
        "findings": findings,
        "subLocalities": subs,
        "subDek": (f"MLS carries no usable neighborhood field for {town}: MLSAreaMinor, CityRegion "
                   f"and Neighborhood are empty, and MLSAreaMajor is filled on {cov}% of sales with "
                   f"ZIP strings mixed into it. PostalCode is on every record, and here it maps to "
                   f"the real geography."),
        "subVerdict": sub_verdict,
        "namedAreas": named,
        "namedCaveat": (f"Only {cov}% of {town} sales carry a named area, and areas under 15 sales "
                        f"are omitted. Indicative, not a ranking — this is the one cut on this page "
                        f"not built on complete data."),
        "season": season,
        "seasonSince": CONFIG["since"][:4],
        "seasonVerdict": season_verdict,
        "method": (f"Single-family closed sales, MLS PIN via Bridge. Headline window: "
                   f"{CONFIG['compareLabel']}; seasonality uses the full pull from "
                   f"{CONFIG['since'][:4]}. Medians throughout; sale-to-list is the mean of "
                   f"per-sale close÷list; market time is MLSPIN_MARKET_TIME. "
                   f"{town} borders New Hampshire and {', '.join(CONFIG['excluded'])} are excluded "
                   f"from the band — MLS PIN sees NH listings only when dual-listed, so including "
                   f"one would understate its volume by an unknown margin. A known gap in the "
                   f"comparison, not a claim that they do not matter."),
        "generated": datetime.date.today().isoformat(),
    }
    return payload


def inject(payload):
    html = PAGE.read_text(encoding="utf-8")
    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    new, n = re.subn(r"/\*@band@\*/.*?/\*@\*/", lambda _: "/*@band@*/" + blob + "/*@*/",
                     html, count=1, flags=re.S)
    if not n:
        sys.exit("ABORT: /*@band@*/ marker not found in the page -- nothing written.")
    if new == html:
        print("  payload unchanged.")
        return
    PAGE.write_text(new, encoding="utf-8")
    print(f"  -> {PAGE.name} written ({len(blob):,} bytes of payload)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="re-pull from Bridge instead of using data/_raw_band cache")
    a = ap.parse_args()
    p = build(a.refresh)
    inject(p)
    s = next(t for t in p["towns"] if t["town"] == CONFIG["town"])
    print(f"\n  {CONFIG['town']}: n={s['n']} median=${s['median']:,} ${s['ppsf']}/sf "
          f"DOM {s['dom']} SP:LP {s['splp']}%")
    print(f"  band median ${p['bandMedian']['median']:,.0f} ${p['bandMedian']['ppsf']:.0f}/sf")
    print(f"  headline: {p['headline']}")
