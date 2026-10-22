#!/usr/bin/env python3
"""US Treasury gold reserve, from Treasury's own Fiscal Data API.

WHAT AND WHY
MASTER_DATA.md carried five gold rows -- total holdings, the three depositories
and a claim that holdings have been flat since 2012 -- each marked hand
verified against "Treasury.gov". They were right when checked on 2026-10-21,
to the ounce. But "right when a human last looked" is the state that let a
wrong HomeBASE figure keep a verified tick for six weeks, so they are written
here instead.

Treasury publishes the Status Report of U.S. Government Gold Reserve monthly.
The Fiscal Data API serves it as JSON with no key:

  https://api.fiscaldata.treasury.gov/services/api/fiscal_service/
    v2/accounting/od/gold_reserve

One row per facility per location per month. Summing every row for the newest
record_date reproduces the published total.

THE FLATNESS CLAIM IS COMPUTED, NOT ASSERTED
"Flat / zero change" is the kind of sentence that stays on a page long after it
stops being true. It is derived here by comparing the newest total against the
earliest record in the series, and the row says what the change actually was.

Exit 75 (EX_TEMPFAIL) when Treasury does not answer -- a neutral skip that
leaves the published figures alone, the convention the other updaters use.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "scripts"))
import register  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "data", "gold-reserve-latest.json")
API = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
       "/v2/accounting/od/gold_reserve")
UA = {"User-Agent": "MA-Data-Hub/1.0 (+https://massachusettsdatahub.com)"}
EXIT_BLOCKED = 75

# The three depositories as Treasury names them, mapped to the register's rows.
DEPOTS = {
    "Fort Knox, KY": "Fort Knox",
    "West Point, NY": "West Point",
    "Denver, CO": "Denver",
}


def blocked(msg):
    print(f"\n{msg}")
    print("Nothing written; the published figures stand. Exit 75 = neutral skip.")
    sys.exit(EXIT_BLOCKED)


def get(params, tries=3):
    url = API + "?" + urllib.parse.urlencode(params, safe=":,-[]")
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            if attempt < tries - 1:
                import time
                time.sleep(4 * (attempt + 1))
    blocked(f"Treasury Fiscal Data did not answer after {tries} tries: "
            f"{type(last).__name__}: {last}")


def oz(rows):
    return sum(float(r.get("fine_troy_ounce_qty") or 0) for r in rows)


def snapshot(date_str):
    d = get({"filter": f"record_date:eq:{date_str}", "page[size]": "200"})
    return d.get("data") or []


def main():
    print("=== US Treasury gold reserve (Fiscal Data API) ===\n")

    newest = get({"sort": "-record_date", "page[size]": "1"})
    if not newest.get("data"):
        blocked("Treasury returned no rows -- refusing to publish.")
    newest_date = newest["data"][0]["record_date"]

    oldest = get({"sort": "record_date", "page[size]": "1"})
    oldest_date = oldest["data"][0]["record_date"]

    now_rows = snapshot(newest_date)
    then_rows = snapshot(oldest_date)
    if not now_rows:
        blocked(f"no rows for {newest_date} -- refusing to publish.")

    total = oz(now_rows)
    then_total = oz(then_rows)
    by_loc = {}
    for r in now_rows:
        by_loc.setdefault(r.get("location_desc", "?"), []).append(r)
    depots = {label: oz(by_loc.get(name, []))
              for name, label in DEPOTS.items()}

    print(f"  newest report  {newest_date}")
    print(f"  total          {total:>18,.3f} fine troy oz")
    for label, v in depots.items():
        print(f"  {label:<14} {v:>18,.3f}")
    missing = [n for n in DEPOTS if n not in by_loc]
    if missing:
        blocked("Treasury's newest report does not name "
                + ", ".join(missing)
                + " -- the location labels have changed and the depository "
                  "rows would be wrong. Refusing to publish.")

    change = total - then_total
    pct = (change / then_total * 100) if then_total else 0.0
    flat = abs(pct) < 0.5
    print(f"\n  earliest report {oldest_date}  {then_total:,.3f} oz")
    print(f"  change since    {change:+,.3f} oz ({pct:+.3f}%)"
          f"{'  -- flat' if flat else ''}")

    def m(v):
        return f"{v / 1e6:.1f}M"

    doc = {
        "fetched_at": datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": ("US Department of the Treasury, Status Report of "
                   "U.S. Government Gold Reserve, via the Fiscal Data API"),
        "source_url": API,
        "measure": "fine troy ounces held, by facility and location",
        "report_date": newest_date,
        "earliest_report_date": oldest_date,
        "total_fine_troy_oz": round(total, 3),
        "depositories": {k: round(v, 3) for k, v in depots.items()},
        "by_location": {k: round(oz(v), 3) for k, v in by_loc.items()},
        "change_since_earliest": {
            "oz": round(change, 3),
            "pct": round(pct, 4),
            "flat": flat,
        },
        "meta": {"currency": {
            "checked": datetime.date.today().isoformat(),
            "newest_available": newest_date,
            "cadence": "Treasury issues the status report monthly",
        }},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print(f"\nWrote {OUT}")

    src = (f"Treasury Status Report of U.S. Government Gold Reserve, "
           f"{newest_date}, via the Fiscal Data API")
    rows = {
        "Total holdings": (f"{m(total)} fine troy oz", src),
        "Fort Knox": (f"{m(depots['Fort Knox'])} oz", src),
        "West Point": (f"{m(depots['West Point'])} oz", src),
        "Denver": (f"{m(depots['Denver'])} oz", src),
        # A label with its own year span in it goes stale the moment the
        # span moves, and then the row silently stops being written. The
        # span belongs in the value, where this script keeps it current.
        "Holdings change since the earliest report": (
            (f"Flat — {change:+,.0f} oz ({pct:+.3f}%) since {oldest_date}"
             if flat else
             f"{change:+,.0f} oz ({pct:+.2f}%) since {oldest_date}"), src),
    }
    written, miss = register.write_rows(rows, "update-gold-reserve.py",
                                        section="Gold")
    print(f"  MASTER_DATA.md: wrote {len(written)} rows")
    if miss:
        # The flatness row carries its year span in the label, so the old label
        # stays behind when the span moves. Report it rather than guessing.
        print("  NOT FOUND in the register (label may have moved): "
              + ", ".join(miss))
    return 0


if __name__ == "__main__":
    sys.exit(main())
