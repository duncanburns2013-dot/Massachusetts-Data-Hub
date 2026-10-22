#!/usr/bin/env python3
"""Mark the hand-ticked rows in the register's non-4-column tables.

WHY A SECOND PASS
The first audit counted "166 hand-verified rows". It had found every row in a
4-column table and none of the rows in the 3-, 5- and 6-column ones -- the tax
tables carry a URL column, the rate-increase tables have three. 81 more rows
were wearing the same tick and were invisible to the count that was supposed
to find them. The real total was 247.

These follow rules rather than needing to be named one at a time:

  frozen    a statutory rate or a citation to one. NH's Interest & Dividends
            tax is 0% because HB 2 (2023) repealed it; the Meals & Rooms rate
            is 8.5% because RSA 78-A says so. A statute does not drift, and a
            tick implying someone re-checks it every month is theatre. It
            changes when the legislature changes it, which is a news event,
            not a data refresh.
  recheck   anything resting on a survey or a vendor: Census ACS tables, the
            Warren Group's median prices, approved carrier rate filings.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TICK = "✅"

# A row whose SOURCE cell cites a statute, a repeal or a revenue department's
# "taxes at a glance" page is stating law, not measuring anything.
STATUTE = re.compile(
    r"\bRSA\s*\d|\bMGL\b|\bM\.G\.L|\bc\.\s*\d+[A-Z]?\s*§|\bHB\s*\d|\bch\.\s*\d"
    r"|repeal|DRA\b|Department of Revenue Administration"
    r"|taxes-glance|taxes-at-a-glance", re.I)

# A row resting on a survey, a vendor index or an approved filing.
SURVEY = re.compile(
    r"Census|ACS\b|B\d{5}|Warren Group|MLS|BEA\b|BLS\b|KFF|MEPS|AHRQ"
    r"|Division of Insurance|DOI\b|rate filing|approved rate", re.I)


def decide(row):
    if TICK not in row["mark"]:
        return None
    joined = " | ".join(row["cells"])
    if STATUTE.search(joined):
        return (f"{register.FROZEN} statutory rate or citation; changes only "
                f"when the law does")
    if SURVEY.search(joined):
        return (f"{register.RECHECK} re-read by 2027-06-30 — the "
                f"publisher's next release")
    return None


def main():
    before = register.counts()
    total = 0
    for section in ("Tax Burden", "Healthcare & Insurance",
                    "Housing & Real Estate", "Corporate Penalties"):
        done = register.mark_rows(decide, section=section)
        total += len(done)
        print(f"  {section:<28} marked {len(done)}")
    after = register.counts()
    print(f"\n  {total} rows marked")
    print(f"  before: {before}")
    print(f"  after:  {after}")
    left = after["hand"]
    if left:
        print(f"\n  {left} rows still hand-ticked -- they matched neither "
              f"rule, so they need a decision rather than a default.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
