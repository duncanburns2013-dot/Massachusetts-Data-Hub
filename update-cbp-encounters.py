#!/usr/bin/env python3
"""
update-cbp-encounters.py
Refreshes the U.S. Border Patrol Southwest-border series on immigration-dashboard.html
from CBP's published monthly tables.

WHAT THIS SCRIPT MAY AND MAY NOT TOUCH
--------------------------------------
The "Southwest Land Border Encounters by Fiscal Year" chart carries two DIFFERENT
measures as two separate series. They must never be merged:

  1. 'Total SW Border encounters (USBP + OFO)'
     Border Patrol apprehensions between ports of entry PLUS Office of Field
     Operations inadmissibles at ports of entry. Source: DHS OHSS KHSM
     (https://ohss.dhs.gov/khsm/cbp-encounters), Southwest Land Border row.
     OHSS last updated this in Feb 2025 and it currently ends at FY2024, because
     CBP's FY2025+ releases no longer publish the OFO component at all.
     >> This script does NOT touch that series. It is a frozen historical series
        from a different publisher on a different basis. If OHSS ever extends it
        past FY2024, extend it from OHSS -- never from the CBP URLs below, which
        do not contain the OFO component.

  2. 'USBP SW Border encounters (Border Patrol only)'
     The Border Patrol component alone -- a strict SUBSET of measure 1.
     Source for FY2024 onward: the CBP pages fetched below, "Southwest Border
     Total Apprehensions" row, summed across the fiscal year's months.
     >> This script updates ONLY the FY2024+ tail of this series.

This is the resolution of the metric mismatch that previously guarded this file.
The old version fetched CBP *nationwide* encounter URLs and wrote them into a
series labelled 'SW Border Encounters'. Nationwide != Southwest, and encounters
(USBP+OFO) != apprehensions (USBP only); doing that silently mixed three bases
into one labelled series. It is fixed by construction now: the scraped row is
"Southwest Border Total Apprehensions" and the target series is the USBP-only
Southwest series, so the source and the label describe the same thing. Verified
against OHSS at the overlap: OHSS puts FY2024 USBP SW at 1,530,520 (rounded to
the nearest 10); these CBP months sum to 1,530,523.

DO NOT repoint these URLs at a nationwide table, and do not aim this script at
series 1, without re-doing that reconciliation.

No API key needed.
"""
import csv
import glob
import json
import os
import re
import sys
import time
import urllib.error
from datetime import datetime, timezone
from html import unescape
from urllib.request import urlopen, Request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMMIGRATION_HTML = os.path.join(BASE_DIR, "immigration-dashboard.html")

# The dataset labels to write into. Must stay in sync with the chart.
USBP_LABEL = "USBP SW Border encounters (Border Patrol only)"
TOTAL_LABEL = "Total SW Border encounters (USBP + OFO)"
# The row on CBP's pages that this series is defined as.
CBP_ROW = "Southwest Border Total Apprehensions"
CBP_NATIONWIDE_ROW = "Nationwide Total Apprehensions"

# Fiscal year -> CBP page. The bare /nationwide-encounters page always carries the
# current fiscal year; closed years get a -fyNNNN archive page. (Despite the page
# slug saying "encounters", these tables are Border Patrol apprehensions only --
# that is precisely why they feed the USBP series and not the total series.)
FY_PAGES = {
    2025: "https://www.cbp.gov/newsroom/stats/nationwide-encounters-fy2025",
    2026: "https://www.cbp.gov/newsroom/stats/nationwide-encounters",
}

MONTHS = {m: i for i, m in enumerate(
    ["oct", "nov", "dec", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep"], 1)}
MONTH_FULL = {1: "Oct", 2: "Nov", 3: "Dec", 4: "Jan", 5: "Feb", 6: "Mar",
              7: "Apr", 8: "May", 9: "Jun", 10: "Jul", 11: "Aug", 12: "Sep"}


# Exit code for "the source blocked us, nothing was written". Expected and
# self-healing, so callers can treat it as a neutral skip rather than a build
# failure. Distinct from 1, which means the page/parse is genuinely wrong.
# (75 = BSD sysexits EX_TEMPFAIL, same convention as update-nh-figures.py.)
EXIT_BLOCKED = 75

# cbp.gov fronts these pages with a bot filter that 403s a custom agent string.
# "MA-Data-Hub/1.0" was honest and got this feed blocked from 2026-07-16 onward;
# a real browser UA is what actually gets served. Same lesson as primemls.py.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


class Blocked(RuntimeError):
    """The source refused us (403/429) and the retries ran out."""


def fetch(url, max_retries=4):
    last = None
    for attempt in range(max_retries):
        req = Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        try:
            with urlopen(req, timeout=45) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (403, 429, 500, 502, 503, 504) and attempt < max_retries - 1:
                ra = e.headers.get("Retry-After")
                wait = float(ra) if (ra and ra.isdigit()) else 8.0 * (attempt + 1)
                time.sleep(min(wait, 60))
                continue
            if e.code in (403, 429):
                raise Blocked(f"{url}: {last}")
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    raise Blocked(f"{url}: unreachable ({last})")


def parse_month_header(cell):
    """'Oct-24' / 'June-25' -> (fy_month_index, calendar_year). None if not a month."""
    m = re.match(r"([A-Za-z]+)[-\s]*(\d{2,4})$", cell.strip())
    if not m:
        return None
    key = m.group(1).lower()[:3]
    if key not in MONTHS:
        return None
    yr = int(m.group(2))
    return MONTHS[key], (2000 + yr if yr < 100 else yr)


def parse_cbp_table(html, row_name):
    """Pull `row_name` out of the first table. Returns [(fy_month, cal_year, value)]."""
    tables = re.findall(r"<table.*?</table>", html, re.S)
    if not tables:
        return None
    rows = re.findall(r"<tr.*?</tr>", tables[0], re.S)
    header, target = None, None
    for row in rows:
        cells = [unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<t[hd].*?</t[hd]>", row, re.S)]
        if not cells:
            continue
        if header is None and any(parse_month_header(c) for c in cells[1:]):
            header = cells
        elif cells[0].strip().lower() == row_name.lower():
            target = cells
    if not header or not target:
        return None

    out = []
    for i, h in enumerate(header[1:], 1):
        parsed = parse_month_header(h)
        if not parsed or i >= len(target):
            continue
        raw = target[i].strip().replace(",", "")
        if not raw or not raw.lstrip("-").isdigit():
            continue  # '-' = month not yet published
        out.append((parsed[0], parsed[1], int(raw)))
    return out or None


def fy_total(url, row=CBP_ROW):
    """(total, months_reported, first(mi,yr), last(mi,yr), monthly) for a CBP FY page."""
    months = parse_cbp_table(fetch(url), row)
    if not months:
        return None
    months.sort(key=lambda t: t[0])
    return (sum(m[2] for m in months), len(months), months[0][:2], months[-1][:2], months)


def find_chart_data(html, label):
    """(match, [current values]) for the dataset labelled `label`.

    Anchored on the label, which does not change when the data does. The current
    values are read out of the file -- never a constant baked into this script.
    A constant would go stale the first time the script succeeded and then
    silently stop matching (the bug fixed in update-census-data.py).
    """
    m = re.search(r"(label:\s*'" + re.escape(label) + r"'\s*,\s*data:\s*\[)([^\]]*)(\])", html)
    if not m:
        return None, None
    return m, [v.strip() for v in m.group(2).split(",") if v.strip()]


def fmt_month(mi, yr):
    return f"{MONTH_FULL[mi]} {yr}"


# ---------------------------------------------------------------------------
# CSV export — preferred source when one is present
# ---------------------------------------------------------------------------
# CBP's public data portal serves a CSV export that carries BOTH components,
# which the monthly HTML tables below do not: those show the Border Patrol row
# only, which is why this dashboard spent months asserting that CBP had stopped
# publishing the Office of Field Operations figure. It had not.
#
# The export cannot be fetched. The portal is a Tableau embed whose workbook name
# carries the month (CBPNationwideEncountersJULFY26), so the URL moves every
# release, and public.tableau.com answers the .csv endpoint with an AWS WAF
# captcha. So: drop the download in data/_raw_cbp/ and this reads it. No export
# present, and it falls through to scraping exactly as before.
CSV_DIR = os.path.join(BASE_DIR, "data", "_raw_cbp")
SBO_GLOB = "sbo-encounters-*.csv"          # southwest border only, by component
NATIONWIDE_GLOB = "nationwide-encounters-*-aor.csv"

# The dashboard's two series are defined by component. Both count every encounter
# type the component records -- for USBP that is apprehensions plus the Title 42
# expulsions of Mar 2020-May 2023, which is what makes the published FY2023 total
# 2,045,838 rather than the 1,496,067 apprehensions alone.
USBP_COMPONENT = "U.S. Border Patrol"
OFO_COMPONENT = "Office of Field Operations"

# The chart's earlier years come from DHS OHSS, rounded to the nearest 10, and the
# note under it says so. The export covers FY2023 too, and writing that year from
# it changes a published 2,045,840 to 2,045,838 — a two-count "correction" that
# does nothing but put two sources inside one series and make the footnote false.
# Only write the years the page already attributes to CBP.
MIN_CBP_FY = 2024
# The two series have DIFFERENT OHSS coverage, so they have different first
# CBP-sourced years. OHSS publishes the USBP component through FY2023 and the
# total through FY2024, so the total may only be written from FY2025 on. Sharing
# one cutoff rewrote a published 2,135,000 as 2,135,005 — same two-count
# non-correction as FY23, one series over.
MIN_CBP_TOTAL_FY = 2025


def _newest(pattern):
    hits = glob.glob(os.path.join(CSV_DIR, pattern))
    return max(hits, key=os.path.getmtime) if hits else None


def read_csv_export():
    """{fy: {'usbp','ofo','months'}} from the newest SBO export, or None."""
    path = _newest(SBO_GLOB)
    if not path:
        return None, None
    print(f"  CSV export: {os.path.basename(path)}")
    per = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                n = int(row["Encounter Count"])
            except (KeyError, TypeError, ValueError):
                continue
            # "2026 (FYTD)" is a partial year; keep the number, drop the suffix.
            fy = int(row["Fiscal Year"].split()[0])
            d = per.setdefault(fy, {"usbp": 0, "ofo": 0, "months": {}})
            comp = row.get("Component", "")
            if comp == USBP_COMPONENT:
                d["usbp"] += n
                mo = row.get("Month (abbv)", "").strip().title()
                d["months"][mo] = d["months"].get(mo, 0) + n
            elif comp == OFO_COMPONENT:
                d["ofo"] += n
    for fy in sorted(per):
        d = per[fy]
        print(f"    FY{fy}: USBP {d['usbp']:,}  OFO {d['ofo']:,}  "
              f"total {d['usbp'] + d['ofo']:,}  ({len(d['months'])} months)")

    nat = {}
    npath = _newest(NATIONWIDE_GLOB)
    if npath:
        with open(npath, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("Component") != USBP_COMPONENT:
                    continue
                try:
                    nat[int(row["Fiscal Year"].split()[0])] = \
                        nat.get(int(row["Fiscal Year"].split()[0]), 0) + int(row["Encounter Count"])
                except (KeyError, TypeError, ValueError):
                    continue
        print(f"  nationwide export: {os.path.basename(npath)}")
    return per, nat


def main():
    print("=== CBP Border Patrol SW-border update ===\n")

    csv_per, csv_nat = read_csv_export()
    if csv_per:
        print("  using the CSV export (carries OFO; the HTML tables do not).\n")

    fetched, blocked = {}, 0
    if csv_per:
        # Shape the export into what the rest of this script already consumes.
        FYM = {m: i for i, m in enumerate(
            ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"], 1)}
        for fy, d in sorted(csv_per.items()):
            if fy < MIN_CBP_FY:
                continue
            got_months = sorted(((FYM[m], m) for m in d["months"] if m in FYM))
            if not got_months:
                continue
            cal = lambda mi: fy - 1 if mi <= 3 else fy      # Oct-Dec fall in the prior calendar year
            monthly = [(mi, cal(mi), d["months"][m]) for mi, m in got_months]
            fetched[fy] = (d["usbp"], len(got_months),
                           (got_months[0][0], cal(got_months[0][0])),
                           (got_months[-1][0], cal(got_months[-1][0])), monthly)
    else:
        for fy, url in sorted(FY_PAGES.items()):
            print(f"  FY{fy}: {url}")
            try:
                got = fy_total(url)
            except Blocked as e:
                print(f"    !! blocked by the source: {e}")
                blocked += 1
                continue
            except Exception as e:
                print(f"    !! fetch/parse failed: {e}")
                got = None
            if not got:
                print(f"    !! could not read '{CBP_ROW}' -- FY{fy} left as published")
                continue
            total, n, first, last, _ = got
            print(f"    {total:,} across {n} month(s): {fmt_month(*first)} - {fmt_month(*last)}")
            fetched[fy] = got

    if not fetched:
        # Being shut out is not the same as the page having changed shape under
        # us. The first is transient and self-healing; the second needs a human.
        if blocked:
            print("\nEvery page was blocked. Dashboard left untouched.", file=sys.stderr)
            return EXIT_BLOCKED
        print("\nNothing fetched. Dashboard left untouched.")
        return 1

    with open(IMMIGRATION_HTML, "r", encoding="utf-8") as f:
        html = f.read()
    orig = html

    m, current = find_chart_data(html, USBP_LABEL)
    if not m:
        print(f"\n  !! no dataset labelled '{USBP_LABEL}' -- NOT updated")
        return 1

    # Chart labels tell us which slot each FY occupies; never assume a position.
    # Search back to the LAST labels: before the dataset rather than a fixed byte
    # window — a 600-char lookback broke the moment a comment was added above the
    # series, which is a silent "NOT updated" for a reason that has nothing to do
    # with the data. re.findall gives every match in the preceding text; the last
    # one is the chart this dataset belongs to.
    _before = re.findall(r"labels:\s*\[([^\]]*)\]", html[:m.start()])
    lm = _before[-1] if _before else None
    if not lm:
        print("  !! chart labels not found -- NOT updated")
        return 1
    labels = [x.strip().strip("'\"") for x in lm.split(",")]
    if len(labels) != len(current):
        print(f"  !! {len(labels)} labels vs {len(current)} values -- NOT updated")
        return 1

    vals = list(current)
    for fy, (total, n, first, last, _) in sorted(fetched.items()):
        want = {f"FY{str(fy)[-2:]}", f"FY{str(fy)[-2:]}*"}
        idx = next((i for i, l in enumerate(labels) if l in want), None)
        if idx is None:
            print(f"  !! FY{fy} has no bar on this chart -- skipped")
            continue
        if str(total) != vals[idx]:
            print(f"  {labels[idx]}: {vals[idx]} -> {total:,}")
            vals[idx] = str(total)

    if vals != current:
        html = html[:m.start()] + m.group(1) + ",".join(vals) + m.group(3) + html[m.end():]
        print("  USBP series updated.")
    else:
        print("  USBP series already current.")

    # ---- total (USBP + OFO) series -----------------------------------------
    # Only the CSV export carries OFO, so this runs only on that path. The two
    # series are NOT interchangeable: USBP is a strict subset, and filling the
    # total with USBP-only numbers overstates the FY24->FY25 fall (84.5% instead
    # of 79.2%). That is why the cells sat null rather than being approximated.
    if csv_per:
        tm, tcur = find_chart_data(html, TOTAL_LABEL)
        if not tm:
            print(f"  !! no dataset labelled '{TOTAL_LABEL}' -- total series NOT updated")
        elif len(labels) != len(tcur):
            print(f"  !! {len(labels)} labels vs {len(tcur)} total values -- NOT updated")
        else:
            tvals = list(tcur)
            for fy, d in sorted(csv_per.items()):
                if fy < MIN_CBP_TOTAL_FY:
                    continue
                want = {f"FY{str(fy)[-2:]}", f"FY{str(fy)[-2:]}*"}
                idx = next((i for i, l in enumerate(labels) if l in want), None)
                if idx is None:
                    continue
                tot = d["usbp"] + d["ofo"]
                if not d["ofo"]:
                    # No OFO rows for this year: leave whatever is published
                    # rather than write a USBP-only figure into a total series.
                    continue
                if str(tot) != tvals[idx]:
                    print(f"  {labels[idx]} total: {tvals[idx]} -> {tot:,}")
                    tvals[idx] = str(tot)
            if tvals != tcur:
                html = html[:tm.start()] + tm.group(1) + ",".join(tvals) + tm.group(3) + html[tm.end():]
                print("  Total series updated.")
            else:
                print("  Total series already current.")

    # Prose is derived from what was just fetched, not retyped by hand.
    cur_fy = max(fetched)
    total, n, first, last, months = fetched[cur_fy]
    try:
        nat = fy_total(FY_PAGES[cur_fy], CBP_NATIONWIDE_ROW)
    except Exception:
        nat = None

    span = f"{fmt_month(*first)}–{fmt_month(*last)}"
    nat_txt = f" ({nat[0]:,} nationwide)" if nat else ""
    if n >= 12:
        period, tail = f"Full year, {span} =", ""
    else:
        period = f"{span} ="
        tail = f" over the fiscal year's first {n} month{'s' if n != 1 else ''}"
    direction = "risen" if months[-1][2] > months[0][2] else "fallen"
    trend = (f" Within that span the monthly Southwest total has {direction} from "
             f"{months[0][2]:,} in {fmt_month(*first)} to {months[-1][2]:,} in "
             f"{fmt_month(*last)}." if n >= 2 else "")
    callout = (f'<div class="callout callout-green"><strong>FY{cur_fy} so far:</strong> '
               f'{period} <strong>{total:,}</strong> Border Patrol apprehensions at the '
               f'Southwest border{nat_txt}{tail}.{trend} CBP has not published the OFO '
               f'port-of-entry component for FY{cur_fy}, so no total-encounter figure '
               f'exists for the year (CBP monthly tables, summed).</div>')
    cm = re.search(r'<div class="callout callout-green"><strong>FY\d{4} so far:.*?</div>', html, re.S)
    if cm:
        if cm.group(0) != callout:
            html = html[:cm.start()] + callout + html[cm.end():]
            print(f"  FY{cur_fy} callout: rewritten from fetched data.")
    else:
        print("  !! FY callout anchor not found -- NOT updated")

    # Stamp the page with the month this data actually covers, every successful
    # run. Unconditional on purpose: if it only fired when a number moved, a feed
    # that quietly stopped returning new months would keep an old stamp looking
    # current -- which is exactly how this page came to claim February in August.
    stamp = fmt_month(*last)
    sm = re.search(r'(data-field="page-updated">)[^<]*(<)', html)
    if sm:
        new_stamp = sm.group(1) + stamp + sm.group(2)
        if sm.group(0) != new_stamp:
            html = html[:sm.start()] + new_stamp + html[sm.end():]
            print(f"  Page update stamp -> {stamp} (latest month in the data).")
    else:
        print("  !! page-updated anchor not found -- NOT updated")

    # Keep the chart's footnote honest about how much of the year is in the bar.
    nm = re.search(r"FY\d{4}\* = [^,]*, \d+ of 12 months", html)
    if nm:
        new_note = f"FY{cur_fy}* = {span} only, {n} of 12 months"
        if nm.group(0) != new_note:
            html = html[:nm.start()] + new_note + html[nm.end():]
            print("  Chart footnote month-count updated.")
    else:
        print("  !! chart footnote anchor not found -- NOT updated")

    if html != orig:
        with open(IMMIGRATION_HTML, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n  -> {os.path.basename(IMMIGRATION_HTML)} written.")
    else:
        print("\n  No changes needed.")

    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "measure": "USBP Southwest land border encounters (Border Patrol only)",
        "source_row": CBP_ROW,
        "sources": FY_PAGES,
        "note": ("Border Patrol component only. CBP does not publish the OFO "
                 "port-of-entry component for FY2025+, so no total-encounters "
                 "figure exists for those years. The total (USBP+OFO) series on "
                 "the chart comes from OHSS KHSM and ends at FY2024."),
        "fy_totals": {f"FY{fy}": {"total": v[0], "months_reported": v[1],
                                  "first_month": fmt_month(*v[2]),
                                  "last_month": fmt_month(*v[3])}
                      for fy, v in sorted(fetched.items())},
    }
    json_path = os.path.join(BASE_DIR, "data", "cbp-encounters-latest.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Data -> {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
