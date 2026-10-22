#!/usr/bin/env python3
"""Third and last pass: give the remaining ticked rows a date from the
publisher's actual cadence.

These are the rows that survived the first two passes because they are
genuinely periodic -- an IRS revenue procedure, the SSA wage base, DLS City &
Town, a fiscal-year revenue close, EIA Electric Power Monthly, a filed utility
tariff. None is frozen and none has a script here yet, so each gets the date
its publisher actually issues on, not a round number.

Two kinds get frozen instead:
  - a scope decision ("excluded by design"), which is a choice this project
    made and records, not a measurement
  - a methodology statement, which describes a rule rather than a quantity
  - approved plan-year rates, which are set for that year once approved
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TICK = "✅"

# (pattern against the whole row, due date, what to re-read)
CADENCE = [
    (r"Rev\.\s*Proc|irs\.gov", "2026-12-31",
     "the IRS revenue procedure for the next tax year, issued each autumn"),
    (r"ssa\.gov|contribution & benefit base", "2026-12-31",
     "the SSA contribution and benefit base, announced each October"),
    (r"City & Town|DLS\b", "2027-03-31",
     "DLS City & Town, which publishes the average bill each February"),
    (r"DOR FY|fiscal-year-\d+-re|DOR\b", "2027-09-30",
     "the DOR fiscal-year revenue close, published each August"),
    (r"CBO\b", "2026-12-31", "the CBO Monthly Budget Review"),
    (r"Monthly Treasury|Final Monthly Tre|U\.S\. Treasury", "2026-12-31",
     "the Final Monthly Treasury Statement for the fiscal year"),
    (r"ACFR|PERAC|NHRS", "2027-03-31",
     "the annual comprehensive financial report"),
    (r"EIA Electric Power Monthly|EIA\b", "2026-12-31",
     "EIA Electric Power Monthly Table 5.6.A. NOTE: "
     "update-energy-dashboard.py already fetches this series -- these rows "
     "should be wired to it rather than re-read by hand"),
    (r"Eversource|Liberty EnergyNorth|tariff|Rate R\b", "2027-01-31",
     "the filed tariff, when the next rate change takes effect"),
    (r"NH DAS|Monthly Revenue Focus", "2026-12-31",
     "the NH DAS monthly revenue focus"),
    (r"NHFPI|InDepthNH|NH Fiscal Po", "2027-06-30",
     "the NHFPI/InDepthNH analysis it rests on"),
]

# Five rows cite "same", inheriting the source of the row above them, so no
# pattern over their own text can place them. Named outright instead -- a
# label-keyed decision is the honest way to handle a row whose source cell
# does not stand on its own.
BY_LABEL_FREEZE = {
    "Federal corporate receipts FY2024":
        "a closed federal fiscal year's final Treasury figure.",
    "MA annual pension appropriation FY2026":
        "an enacted appropriation for a closed fiscal year.",
    "NH business taxes FY2024":
        "a closed New Hampshire fiscal year's final revenue figure.",
}
BY_LABEL_RECHECK = {
    "**NH residential electricity, all-in**":
        ("2026-12-31", "EIA Electric Power Monthly Table 5.6.A"),
    "**MA annual overpayment vs US average**":
        ("2026-12-31", "derived from the MA and US EIA rates above; "
                       "re-derive when either moves"),
}

FREEZE = [
    (r"excluded by design|Scope decision",
     "a scope decision this project made and records, not a measurement. It "
     "changes only if the model's boundary changes."),
    (r"Which companies are included|Amounts not counted"
     r"|Penalty amounts, dates and agencies",
     "a methodology statement describing a rule, not a quantity."),
]

# The 2026 approved rate increases are set for that plan year.
FREEZE_SECTION = [
    ("Healthcare & Insurance :: 2026 MA Rate Increases",
     "an approved 2026 plan-year rate increase. Once the Division of "
     "Insurance approves the plan year's rates they are set for it; the 2027 "
     "filings are a new row, not a revision of this one."),
]


def decide(row):
    if TICK not in row["mark"]:
        return None
    if row["label"] in BY_LABEL_FREEZE:
        return f"{register.FROZEN} {BY_LABEL_FREEZE[row['label']]}"
    if row["label"] in BY_LABEL_RECHECK:
        when, what = BY_LABEL_RECHECK[row["label"]]
        return f"{register.RECHECK} re-read by {when} — {what}"
    joined = " | ".join(row["cells"])
    for pat, why in FREEZE:
        if re.search(pat, joined, re.I):
            return f"{register.FROZEN} {why}"
    for pat, when, what in CADENCE:
        if re.search(pat, joined, re.I):
            return f"{register.RECHECK} re-read by {when} — {what}"
    return None


def main():
    before = register.counts()
    total = 0
    for sec, why in FREEZE_SECTION:
        done = register.mark_rows(
            lambda r: (f"{register.FROZEN} {why}" if TICK in r["mark"] else None),
            section=sec)
        total += len(done)
        print(f"  frozen by section: {sec[:46]:<46} {len(done)}")
    done = register.mark_rows(decide)
    total += len(done)
    print(f"  by cadence rule:   {len(done)}")
    after = register.counts()
    print(f"\n  {total} rows marked")
    print(f"  before: {before}")
    print(f"  after:  {after}")
    if after["hand"]:
        print(f"\n  {after['hand']} still hand-ticked:")
        for r in register.all_marked_rows():
            if TICK in r["mark"]:
                print("    [%s] %s" % (r["section"][:26],
                                       " | ".join(r["cells"][:3])[:84]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
