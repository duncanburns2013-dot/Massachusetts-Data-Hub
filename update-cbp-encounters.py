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
import json
import os
import re
import sys
from datetime import datetime, timezone
from html import unescape
from urllib.request import urlopen, Request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMMIGRATION_HTML = os.path.join(BASE_DIR, "immigration-dashboard.html")

# The dataset label to write into. Must stay in sync with the chart.
USBP_LABEL = "USBP SW Border encounters (Border Patrol only)"
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


def fetch(url):
    req = Request(url, headers={"User-Agent": "MA-Data-Hub/1.0"})
    with urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


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


def main():
    print("=== CBP Border Patrol SW-border update ===\n")

    fetched = {}
    for fy, url in sorted(FY_PAGES.items()):
        print(f"  FY{fy}: {url}")
        try:
            got = fy_total(url)
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
    lm = re.search(r"labels:\s*\[([^\]]*)\]", html[max(0, m.start() - 600):m.start()])
    if not lm:
        print("  !! chart labels not found -- NOT updated")
        return 1
    labels = [x.strip().strip("'\"") for x in lm.group(1).split(",")]
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
