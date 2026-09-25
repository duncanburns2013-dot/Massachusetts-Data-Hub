#!/usr/bin/env python3
"""update-mbta-3a.py -- refresh the MBTA Communities Act (MGL c. 40A s 3A) page
from EOHLC's own published tables.

WHY THIS EXISTS
---------------
This dashboard began as a 660KB minified React bundle in a separate repository,
with the town table, the capacity totals and the compliance counts frozen inside
it. That copy had drifted badly: its town table held 161 rows under a heading
that said "All 177 Communities", its capacity total summed to 273,080 while its
own prose quoted 297,190, and its category counts matched neither. None of it
could be checked, because there was no source and nothing fetched anything.

EOHLC publishes all three of the tables that page was reproducing, and keeps
them current. So the page now reads them.

SOURCE
------
Executive Office of Housing and Livable Communities:
  https://www.mass.gov/info-details/multi-family-zoning-requirement-for-mbta-communities

Three CSVs are linked from that page:
  1. Community categories and capacity calculations  (177 rows, the mandate)
  2. Compliance Status Sheet                          (177 rows, the determinations)
  3. 3A Development Tracker                           (what has actually been proposed/built)

THE URLS MOVE, SO THEY ARE NOT HARDCODED
----------------------------------------
Two of the three filenames carry the date of the edition -- "Compliance Status
Sheet as of 8-31-26.csv", "3A Development Tracker as of 9-11-26.csv". Hardcoding
those would pin the page to one edition and then 404 silently the moment EOHLC
published the next one, which is exactly the failure this repository keeps
finding. The links are scraped from the page instead, and the edition date is
read back out of the filename so the page can print which edition it is showing.

TRANSPORT
---------
mass.gov returns 403 to a bare request, which is why an earlier note in this
repo concluded mass.gov "blocks bots". It does not fingerprint the client the
way cbp.gov does -- the filter is header-based, and a full browser header set
gets 200 from plain curl. Verified 2026-09-25 from this machine and required for
the scheduled run to work at all.
"""
import csv
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "mbta-3a-dashboard.html")
DATA_FILE = os.path.join(BASE_DIR, "data", "mbta-3a-latest.json")
PAGE_URL = ("https://www.mass.gov/info-details/"
            "multi-family-zoning-requirement-for-mbta-communities")

EXIT_BLOCKED = 75

# mass.gov's edge rejects requests that do not look like a browser navigation.
HEADERS = [
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "-H", "Accept: text/csv,text/html,application/xhtml+xml,*/*;q=0.8",
    "-H", "Accept-Language: en-US,en;q=0.9",
    "-H", f"Referer: {PAGE_URL}",
    "-H", "Sec-Fetch-Dest: empty",
    "-H", "Sec-Fetch-Mode: cors",
    "-H", "Sec-Fetch-Site: same-origin",
]

EXPECTED_COMMUNITIES = 177   # fixed by which municipalities the MBTA serves


def blocked(msg):
    print(f"SKIPPED: {msg}", file=sys.stderr)
    sys.exit(EXIT_BLOCKED)


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def fetch(url):
    """Text of a mass.gov URL, or None. Never raises on a transport problem --
    the caller decides between a neutral skip and a hard failure."""
    fd, out = tempfile.mkstemp()
    os.close(fd)
    try:
        r = subprocess.run(
            ["curl", "-sSL", "--compressed", "--max-time", "90", "--retry", "3",
             "--retry-delay", "2", "-o", out, "-w", "%{http_code}", *HEADERS, url],
            capture_output=True, text=True, timeout=180)
        if r.returncode != 0 or r.stdout.strip() != "200":
            return None
        with open(out, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except (subprocess.SubprocessError, OSError):
        return None
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


def find_csv_links(page):
    """The CSV links on the EOHLC page, in document order.

    EOHLC renders three tables and puts a 'Download table data as CSV' link
    under each, so order identifies them: capacity, compliance status,
    development tracker.
    """
    # The hrefs are absolute (https://www.mass.gov/files/csv/...), not rooted
    # paths. A regex that assumed "/files/csv" found nothing and reported the
    # page layout as changed, which is the wrong diagnosis to hand a reader.
    found = re.findall(r'href="((?:https?://[^"/]+)?/files/csv/[^"]+\.csv)"',
                       page, re.I)
    return [u if u.startswith("http") else "https://www.mass.gov" + u
            for u in dict.fromkeys(found)]


def edition(url, default):
    """The 'as of' date out of a filename like '...as of 8-31-26.csv'."""
    # The URL is percent-encoded, so "as of 9-11-26" arrives as
    # "as%20of%209-11-26" and a match on spaces alone silently falls through to
    # the coarse year-month fallback -- which then prints the wrong edition on
    # the page. Decode before reading the date out of it.
    url = urllib.parse.unquote(url)
    m = re.search(r"as\s*of\s*(\d{1,2})-(\d{1,2})-(\d{2})", url, re.I)
    if not m:
        m2 = re.search(r"/(\d{4})-(\d{2})/", url)
        if m2:
            return f"{m2.group(1)}-{m2.group(2)}"
        return default
    mm, dd, yy = (int(x) for x in m.groups())
    return date(2000 + yy, mm, dd).isoformat()


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def num(x):
    d = re.sub(r"[^0-9.-]", "", str(x or ""))
    try:
        return int(float(d))
    except ValueError:
        return 0


def col(row, *names):
    """Header text on these CSVs carries stray spaces and footnote markers."""
    norm = {re.sub(r"[^a-z0-9]", "", (k or "").lower()): v for k, v in row.items()}
    for n in names:
        key = re.sub(r"[^a-z0-9]", "", n.lower())
        for k, v in norm.items():
            if k.startswith(key):
                return (v or "").strip()
    return ""


def main():
    print("=== MBTA Communities Act s 3A (EOHLC) ===\n")

    page = fetch(PAGE_URL)
    if page is None:
        blocked("EOHLC's MBTA Communities page did not answer -- the dashboard "
                "keeps the figures it has.")
    links = find_csv_links(page)
    if len(links) < 3:
        blocked(f"found {len(links)} CSV links on the EOHLC page, expected 3. "
                f"The page layout may have changed; nothing written.")

    cap_u, sta_u, dev_u = links[:3]
    texts = {}
    for name, url in (("capacity", cap_u), ("status", sta_u), ("tracker", dev_u)):
        t = fetch(url)
        if t is None:
            blocked(f"EOHLC did not serve the {name} CSV.")
        texts[name] = t

    cap, sta, dev = rows(texts["capacity"]), rows(texts["status"]), rows(texts["tracker"])
    if len(cap) != EXPECTED_COMMUNITIES:
        fail(f"capacity table has {len(cap)} rows, expected {EXPECTED_COMMUNITIES}. "
             f"Nothing written.")
    if len(sta) != EXPECTED_COMMUNITIES:
        fail(f"compliance table has {len(sta)} rows, expected "
             f"{EXPECTED_COMMUNITIES}. Nothing written.")

    status = {}
    for r in sta:
        status[col(r, "Municipality", "Community").strip()] = {
            "status": col(r, "Compliance Status") or "Unknown",
            "adopted": col(r, "Adopted zoning"),
            "deadline": col(r, "Compliance Deadlines"),
        }

    # The tracker has one row per development, so it aggregates to the town.
    track = {}
    for r in dev:
        m = col(r, "Municipality").strip()
        if not m:
            continue
        t = track.setdefault(m, {"projects": 0, "units": 0, "net": 0, "deed": 0})
        t["projects"] += 1
        t["units"] += num(col(r, "# Total Units", "Total Units"))
        t["net"] += num(col(r, "Net Units"))
        t["deed"] += num(col(r, "Deed_Restricted", "Deed Restricted"))

    towns, unmatched = [], []
    for r in cap:
        n = col(r, "Community", "Municipality").strip()
        st = status.get(n)
        if st is None:
            unmatched.append(n)
            st = {"status": "Unknown", "adopted": "", "deadline": ""}
        t = track.get(n, {"projects": 0, "units": 0, "net": 0, "deed": 0})
        towns.append({
            "n": n,
            "c": col(r, "Community category"),
            "h": num(col(r, "2020 Housing Units")),
            "r": num(col(r, "Minimum multi-family unit capacity")),
            "pct": num(col(r, "Unit capacity % of Total Housing units")),
            "status": st["status"],
            "adopted": st["adopted"],
            "deadline": st["deadline"],
            "projects": t["projects"],
            "units": t["units"],
            "net": t["net"],
            "deed": t["deed"],
        })
    if unmatched:
        # A name that does not join is a silently wrong row, not a missing one.
        fail(f"{len(unmatched)} communities in the capacity table have no "
             f"compliance row ({', '.join(unmatched[:5])}). Nothing written.")

    stock = sum(t["h"] for t in towns)
    required = sum(t["r"] for t in towns)
    units = sum(t["units"] for t in towns)
    deed = sum(t["deed"] for t in towns)
    projects = sum(t["projects"] for t in towns)
    active = sum(1 for t in towns if t["projects"])
    by_status = {}
    for t in towns:
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
    by_cat = {}
    for t in towns:
        by_cat[t["c"]] = by_cat.get(t["c"], 0) + 1

    # How many communities are required to zone above their category's nominal
    # share. The 50-acre minimum land area at 15 units/acre sets a ~750-unit
    # floor that overrides the percentage in a small town.
    BASELINE = {"Rapid Transit": 25, "Commuter Rail": 15,
                "Adjacent community": 10, "Adjacent small town": 5}
    over_base = sum(1 for t in towns if t["pct"] > BASELINE.get(t["c"], 99))
    gtown = next((t["pct"] for t in towns if t["n"] == "Georgetown"), 0)

    if not required:
        fail("required capacity summed to zero -- the capacity column did not "
             "parse. Nothing written.")

    sta_date = edition(sta_u, "")
    dev_date = edition(dev_u, "")
    today = date.today()

    print(f"  communities      {len(towns)}")
    print(f"  2020 housing     {stock:,}")
    print(f"  required capacity{required:>9,}")
    print(f"  compliance       {by_status}")
    print(f"  categories       {by_cat}")
    print(f"  tracker          {projects} developments, {units:,} units, "
          f"{deed:,} deed-restricted, {active} communities "
          f"(edition {dev_date or 'undated'})")

    with open(HTML_FILE, encoding="utf-8") as fh:
        html = original = fh.read()

    def setf(tag, value):
        nonlocal html
        pat = r'(data-field="' + re.escape(tag) + r'">)[^<]*(<)'
        new, n = re.subn(pat, lambda m: m.group(1) + value + m.group(2), html)
        if n == 0:
            print(f"  WARNING: no data-field \"{tag}\" -- left as it was")
        html = new

    def marker(tag, value):
        nonlocal html
        pat = r"(/\*@" + re.escape(tag) + r"\*/).*?(/\*@\*/)"
        new, n = re.subn(pat, lambda m: m.group(1) + value + m.group(2),
                         html, count=1, flags=re.S)
        if n == 0:
            fail(f"marker /*@{tag}*/ is missing from the page. Nothing written.")
        html = new

    marker("towns", json.dumps(towns, separators=(",", ":"), ensure_ascii=False))

    nice = today.strftime("%-d %B %Y") if os.name != "nt" else \
        f"{today.day} {today.strftime('%B %Y')}"

    def pretty(iso, fallback):
        if not iso:
            return fallback
        try:
            d = date.fromisoformat(iso)
        except ValueError:
            return fallback
        return f"{d.day} {d.strftime('%B %Y')}"

    for tag, val in (
        ("kpi-communities", str(len(towns))),
        ("kpi-communities2", str(len(towns))),
        ("kpi-communities3", str(len(towns))),
        ("kpi-required", f"{required:,}"),
        ("kpi-required2", f"{required:,}"),
        ("kpi-required3", f"{required:,}"),
        ("kpi-stock", f"{stock:,}"),
        ("kpi-sharestock", f"{required / stock * 100:.1f}%"),
        ("kpi-builtunits", f"{units:,}"),
        ("kpi-builtunits2", f"{units:,}"),
        ("kpi-projects", str(projects)),
        ("kpi-deed", f"{deed:,}"),
        ("kpi-active", str(active)),
        ("pr-pipeshare", f"{units / required * 100:.1f}%"),
        ("pr-builtunits", f"{units:,}"),
        ("pr-required", f"{required:,}"),
        ("pr-active", str(active)),
        ("pr-communities", str(len(towns))),
        ("pr-deedshare", f"{deed / units * 100:.1f}%" if units else "n/a"),
        ("pr-overbase", str(over_base)),
        ("pr-communities2", str(len(towns))),
        ("pr-gtown", f"{gtown}%" if gtown else "its category's share"),
        ("src-retrieved", nice),
        ("src-retrieved2", nice),
        ("src-retrieved3", nice),
        ("src-status-date", pretty(sta_date, "the current edition")),
        ("src-dev-date", pretty(dev_date, "the current edition")),
        ("src-dev-date2", pretty(dev_date, "the current edition")),
    ):
        setf(tag, val)

    out = {
        "communities": len(towns),
        "housing_units_2020": stock,
        "required_capacity": required,
        "required_share_of_stock_pct": round(required / stock * 100, 2),
        "by_category": by_cat,
        "by_compliance_status": by_status,
        "tracker": {
            "developments": projects, "total_units": units,
            "net_units": sum(t["net"] for t in towns),
            "deed_restricted": deed,
            "communities_with_activity": active,
            "units_as_pct_of_required": round(units / required * 100, 2),
            "deed_restricted_pct_of_tracked": (round(deed / units * 100, 2)
                                               if units else None),
            "edition": dev_date or None,
        },
        "compliance_edition": sta_date or None,
        "towns": towns,
        "verified": today.isoformat(),
        "source": "Massachusetts Executive Office of Housing and Livable "
                  "Communities -- published category/capacity table, Compliance "
                  "Status Sheet, and 3A Development Tracker",
        "source_url": PAGE_URL,
        "source_files": {"capacity": cap_u, "compliance": sta_u, "tracker": dev_u},
        "notes": ("Required capacity is zoned capacity under EOHLC's compliance "
                  "model, not a construction requirement. Tracker rows mix "
                  "completed, permitted and proposed developments and EOHLC "
                  "states the list may not be comprehensive."),
        "meta": {"currency": {
            "checked": today.isoformat(),
            "newest_available": dev_date or today.isoformat(),
            "cadence": "EOHLC reissues the compliance sheet and the development "
                       "tracker every few weeks; the capacity table changes rarely",
        }},
    }
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    prev = None
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, encoding="utf-8") as fh:
                prev = json.load(fh)
        except (OSError, ValueError):
            prev = None
    strip = lambda d: ({k: v for k, v in d.items()
                        if k not in ("verified", "meta")} if d else None)
    if prev is not None and strip(prev) == strip(out):
        out["verified"] = prev.get("verified", out["verified"])
        out["meta"]["currency"]["checked"] = (
            prev.get("meta", {}).get("currency", {})
                .get("checked", out["meta"]["currency"]["checked"]))

    if html == original:
        print("\n  No changes needed.")
    else:
        with open(HTML_FILE, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"\n  Updated {os.path.basename(HTML_FILE)}")
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"Data -> {DATA_FILE}")


if __name__ == "__main__":
    main()
