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


def main():
    print("=== MA domestic migration ===" + NL)
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
    }
    with io.open(OUT, "w", encoding="utf-8", newline=NL) as f:
        json.dump(payload, f, indent=1)
        f.write(NL)
    print(f"  {OUT}: {left:,} net out, {first}-{last}")
    for y in sorted(years):
        print(f"    {y}  {years[y]:+8,}")

    # ── stamp the page ──
    if not os.path.exists(PAGE):
        fail(f"{PAGE} not found")
        return 1
    html = io.open(PAGE, encoding="utf-8").read()
    orig = html

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
