# -*- coding: utf-8 -*-
"""Refresh Massachusetts net domestic out-migration from the Census Bureau.

WHY THIS EXISTS
The immigration dashboard carried "137K -- MA Residents Left" as a bare number:
no period, no source, no Method row, and no feed behind it. Nothing could age it
and nothing could check it, so when Census published its 2025 vintage -- adding a
year and revising every prior one -- the card stayed where it was. A Boston
Herald piece on 8 September 2026 quoted Pioneer Institute at 182,000 while the
site still said 137K, which is how the gap surfaced: a reader found it, not us.

That is the failure this file removes. The figure now comes from the Census
file Pioneer itself reads, so the two cannot disagree, and it is stamped,
sourced and documented like every other figure on the site.

WHAT IT COUNTS
Net DOMESTIC migration only: people moving between states. It excludes
international arrivals, births and deaths, so it is not population change and
must never be labelled as such. Cumulative since 2020, which is the span the
public argument is about.

SOURCE
census.gov's own population-estimates release, the key-free bulk CSV rather than
the API -- the API needs a key that only exists in repository secrets, and this
number should be reproducible by anyone who runs the script.

  https://www2.census.gov/programs-surveys/popest/datasets/
      2020-<vintage>/state/totals/NST-EST<vintage>-ALLDATA.csv

The vintage is discovered by trying years downward from next year, so a new
release is picked up without editing this file. Each vintage RESTATES earlier
years, so the whole series is re-summed every run rather than accumulated -- the
2024 vintage put 2020-2024 at 162,751 and the 2025 vintage puts the same span at
148,805. Adding a year to a stored total would bake in the old revision.

THE OTHER COMPONENTS
The page's year-by-year table, KPIs and charts also show international
migration, natural change and population change. Those were hand-typed, and by
October 2026 they sat on an older vintage while the domestic column was current:
2024-25 international read +56,600 where vintage 2025 says +40,240. So every
component now comes from the same row of the same file, and the page is stamped
through data-mig anchors plus one fenced MIG object the charts read. If Census
adds a year the table has no row for, nothing is written and the run fails:
a human adds the row. Run locally behind the proxy with --csv <file>.
"""
import datetime
import io
import json
import os
import re
import sys
import urllib.request

NL = chr(10)
ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "immigration-dashboard.html")
OUT = os.path.join(ROOT, "data", "domestic-migration-latest.json")
UA = {"User-Agent": "MA-Data-Hub/1.0 (+https://massachusettsdatahub.com)"}

URL = ("https://www2.census.gov/programs-surveys/popest/datasets/"
       "2020-{v}/state/totals/NST-EST{v}-ALLDATA.csv")

failures = []


def fail(msg):
    failures.append(msg)
    print("  !! " + msg)


def fetch_latest():
    """Newest published vintage. Returns (vintage, csv_text) or (None, None)."""
    # One year ahead of today, because a vintage is released in December for the
    # year it names; from January onwards that file is the current one.
    for v in range(datetime.date.today().year + 1, 2019, -1):
        try:
            req = urllib.request.Request(URL.format(v=v), headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                if r.status == 200:
                    print(f"  Census vintage {v}")
                    return v, r.read().decode("utf-8-sig", "replace")
        except Exception:
            continue
    return None, None


def ma_row(text):
    import csv
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("NAME") == "Massachusetts":
            return row
    return None


# short name -> Census column stem. NPOPCHG is the only stem with an underscore.
COMP = (("dom", "DOMESTICMIG"), ("intl", "INTERNATIONALMIG"),
        ("nat", "NATURALCHG"), ("netmig", "NETMIG"),
        ("popchg", "NPOPCHG"), ("resid", "RESIDUAL"))

MIG_F0, MIG_F1 = "/* == mig-data start == */", "/* == mig-data end == */"
ANCHOR = re.compile(r'(<(\w+)\b[^>]*\bdata-mig="([^"]+)"[^>]*>)[^<]*(</\2>)')


def series(row, stem):
    out = {}
    for k, v in row.items():
        m = re.fullmatch(stem + r"_?(\d{4})", k or "")
        if m:
            try:
                out[int(m.group(1))] = int(v)
            except (TypeError, ValueError):
                continue
    return out


def components(row, years):
    """Rows as the page shows them, plus every value the page anchors.

    Returns (rows, vals) or (None, None) after recording a failure."""
    comps = {s: series(row, stem) for s, stem in COMP}
    for s, c in comps.items():
        if sorted(c) != sorted(years):
            fail(f"{s} covers {sorted(c)}, domestic covers {sorted(years)} -- refusing to publish")
            return None, None
    for y in years:
        c = {s: comps[s][y] for s in comps}
        if c["netmig"] != c["dom"] + c["intl"] or \
           c["popchg"] != c["nat"] + c["netmig"] + c["resid"]:
            fail(f"{y}: components do not add up in the Census file -- refusing to publish")
            return None, None

    # Census dates the series from 1 April 2020, so its first "year" is a
    # three-month stub. The page folds it into the first full year.
    ys = sorted(years)
    rows = []
    for g in [ys[:2]] + [[y] for y in ys[2:]]:
        r = {"label": f"{g[-1] - 1}-{str(g[-1])[2:]}"}
        r.update({s: sum(comps[s][y] for y in g) for s in comps})
        rows.append(r)
    tot = {s: sum(r[s] for r in rows) for s in comps}

    sg = lambda n: f"{n:+,}"
    vals = {}
    for r in rows + [dict(tot, label="total")]:
        for s in comps:
            vals[f"{r['label']}.{s}"] = sg(r[s])
    for y in ys:
        for s in comps:
            vals[f"y{y}.{s}"] = sg(comps[s][y])

    if tot["dom"] >= 0 or tot["dom"] + tot["nat"] >= 0:
        fail("domestic or domestic-plus-natural is not negative -- the page copy "
             "says people left and the state would have shrunk; needs a human")
        return None, None
    a, b = rows[-2], rows[-1]
    if a["dom"] >= 0 or b["dom"] >= 0:
        fail("a recent year shows net domestic IN-migration -- 'exodus' copy needs a human")
        return None, None

    def change(x, y):
        pct = (y - x) / x * 100
        return f"{'↓' if pct < 0 else '↑'}{abs(pct):.0f}% ({x / 1000:.0f}K→{y / 1000:.0f}K)"

    vals.update({
        "total.dom.abs": f"{-tot['dom']:,}",
        "total.intl.abs": f"{tot['intl']:,}",
        "noimm": f"{-(tot['dom'] + tot['nat']):,}",
        "ratio": f"{tot['intl'] / -tot['dom']:.1f}",
        "last.label": b["label"],
        "intl.chg": change(a["intl"], b["intl"]),
        "dom.chg": change(-a["dom"], -b["dom"]),
    })
    return rows, vals


def stamp_components(html, rows, vals, vintage):
    """Write every data-mig anchor and the MIG object. Fails on anything the
    page and the data disagree about, before a single value is written."""
    vals = dict(vals, vintage=str(vintage))
    keys = [m.group(3) for m in ANCHOR.finditer(html)]
    if not keys:
        fail("no data-mig anchors in the page -- components NOT stamped")
        return None
    unknown = sorted(set(keys) - set(vals))
    missing = [r["label"] for r in rows if f"{r['label']}.dom" not in keys]
    if unknown:
        fail("page anchors with no Census value: " + ", ".join(unknown))
    if missing:
        fail("Census has years the table has no row for: " + ", ".join(missing))
    if MIG_F0 not in html or MIG_F1 not in html:
        fail("MIG fences missing from the page")
    if unknown or missing or MIG_F0 not in html or MIG_F1 not in html:
        return None

    html = ANCHOR.sub(lambda m: m.group(1) + vals[m.group(3)] + m.group(4), html)
    mig = {"vintage": vintage, "labels": [r["label"] for r in rows]}
    mig.update({s: [r[s] for r in rows] for s, _ in COMP})
    a, b = html.index(MIG_F0), html.index(MIG_F1) + len(MIG_F1)
    return html[:a] + MIG_F0 + NL + "var MIG=" + json.dumps(mig, separators=(",", ":")) + \
        ";" + NL + MIG_F1 + html[b:]


def main():
    print("=== MA domestic migration ===" + NL)
    if "--csv" in sys.argv:
        path = sys.argv[sys.argv.index("--csv") + 1]
        vintage = int(re.search(r"NST-EST(\d{4})", os.path.basename(path)).group(1))
        text = io.open(path, encoding="utf-8-sig").read()
        print(f"  Census vintage {vintage} (local file {path})")
    else:
        vintage, text = fetch_latest()
    if not text:
        fail("no Census vintage reachable -- nothing updated")
        return 1

    row = ma_row(text)
    if not row:
        fail("Massachusetts row not found in the Census file")
        return 1

    years = {}
    for k, v in row.items():
        m = re.fullmatch(r"DOMESTICMIG(\d{4})", k or "")
        if m:
            try:
                years[int(m.group(1))] = int(v)
            except (TypeError, ValueError):
                continue
    if len(years) < 3:
        fail(f"only {len(years)} yearly values found -- refusing to publish a partial series")
        return 1

    net = sum(years.values())
    if net > 0:
        fail(f"net domestic migration is positive ({net:+,}) -- the label says "
             "out-migration, so this needs a human before it publishes")
        return 1

    rows, vals = components(row, years)
    if rows is None:
        return 1

    if not os.path.exists(PAGE):
        fail(f"{PAGE} not found")
        return 1
    html = io.open(PAGE, encoding="utf-8").read()
    orig = html
    html = stamp_components(html, rows, vals, vintage)
    if html is None:
        print("  nothing written")
        return 1

    left = -net
    first, last = min(years), max(years)
    payload = {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc)
                              .isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "U.S. Census Bureau, Population Estimates Program (NST-EST components of change)",
        "source_url": URL.format(v=vintage),
        "vintage": vintage,
        "measure": "net domestic migration (interstate only; excludes international, births, deaths)",
        "span": f"{first}-{last}",
        "net_domestic_outmigration": left,
        "by_year": {str(y): years[y] for y in sorted(years)},
        "latest_year": last,
        "latest_year_net": years[last],
        # every component, per Census year, from the same row of the same file
        "components": {s: {str(y): series(row, stem)[y] for y in sorted(years)}
                       for s, stem in COMP},
    }
    with io.open(OUT, "w", encoding="utf-8", newline=NL) as f:
        json.dump(payload, f, indent=1)
        f.write(NL)
    print(f"  {OUT}: {left:,} net out, {first}-{last}")
    for y in sorted(years):
        print(f"    {y}  {years[y]:+8,}")

    for r in rows:
        print(f"    {r['label']}  intl {r['intl']:+8,}  nat {r['nat']:+7,}  pop {r['popchg']:+8,}")

    # ── stamp the page ──
    pretty = f"{round(left / 1000):,}K"
    span = f"{first}–{str(last)[2:]}"          # 2020–25
    for field, value in (("net-outmigration", pretty),
                         ("net-outmigration-span", span)):
        pat = re.compile(r'(<span data-field="%s">)[^<]*(</span>)' % field)
        if pat.search(html):
            html = pat.sub(lambda m: m.group(1) + value + m.group(2), html)
        else:
            fail(f'anchor data-field="{field}" not found -- NOT updated')

    if html != orig:
        io.open(PAGE, "w", encoding="utf-8", newline=NL).write(html)
        print(f"  page stamped -> {pretty} ({span})")
    else:
        print("  page already current")

    if failures:
        print(NL + f"{len(failures)} problem(s) above.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
