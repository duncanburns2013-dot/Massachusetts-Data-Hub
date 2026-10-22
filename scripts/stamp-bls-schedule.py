#!/usr/bin/env python3
"""Write the BLS release-date rows in MASTER_DATA.md from the JSON.

WHY
data/bls-release-schedule.json is already the authoritative copy -- it is what
fetch-bls-data.js reads to stamp a release date on the employment dashboard,
and its own header explains why the dates cannot be computed: there is no
first-Friday rule. The register carried the same 26 dates typed a second time.

Two copies of the same 26 facts, both hand-kept, is a disagreement waiting to
happen. They agree today; this makes that structural rather than lucky. The
JSON stays the thing a human tops up from bls.gov (which blocks bots), and the
register becomes a rendering of it.

Idempotent. Run it after topping up the JSON.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = os.path.join(ROOT, "data", "bls-release-schedule.json")

# The two tables, and the sub-heading each lives under.
TABLES = [
    ("employment_situation", "National", "BLS Employment Situation schedule"),
    ("state_employment", "Massachusetts",
     "BLS State Employment and Unemployment schedule"),
]


def main():
    with open(FEED, encoding="utf-8") as fh:
        feed = json.load(fh)

    total, missing_all = 0, []
    for key, subheading, source in TABLES:
        rows = {}
        for ref, iso in feed.get(key, {}).items():
            try:
                label = datetime.datetime.strptime(ref, "%Y-%m").strftime("%B %Y")
                shown = datetime.datetime.strptime(
                    iso, "%Y-%m-%d").strftime("%b %d, %Y")
            except ValueError:
                print(f"  skipping unparseable entry {ref} -> {iso}")
                continue
            rows[label] = (shown, source)
        written, missing = register.write_rows(
            rows, "scripts/stamp-bls-schedule.py", section=subheading)
        total += len(written)
        print(f"  {key:<22} wrote {len(written)} rows")
        # A month in the JSON with no register row is normal -- the JSON runs
        # ~13 months ahead of what the register tabulates. Only report the
        # reverse, which this cannot see, so nothing is raised here.
        missing_all.extend(missing)
    print(f"\n  {total} release-date rows now written from "
          f"data/bls-release-schedule.json")
    if total == 0:
        print("  WARNING: nothing matched. Check the sub-headings in "
              "MASTER_DATA.md against TABLES above.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
