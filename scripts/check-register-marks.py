#!/usr/bin/env python3
"""Fail if a register row carries a bare hand-verified tick.

Every row in MASTER_DATA.md must say how it is held up:

  written by a script   a job refreshes it
  frozen                it cannot change, and why
  re-read by <date>     a human reads it, and when they are next due

A bare tick says none of those. It reads as assurance and carries none: it is
identical on a row a script could own, on a row nobody will ever check again,
and on a row that needed re-reading last quarter. The wrong HomeBASE figure
wore one for six weeks.

A new row added with a tick fails here, which is the point -- the marks only
stay honest if adding a dishonest one is noisy.

IT ALSO FAILS ON A RE-READ DATE THAT HAS PASSED, added 2026-11-22.

Until then this script counted the kinds of mark and never compared a date to
today. "re-read by 2026-10-31" was accepted in November exactly as it had been
accepted in September: the date was recorded and nothing ever rang. A promise
with no alarm is the same bare tick in a longer sentence, which is the thing
this file was written to stop.

It was found the way these things are found -- the first lapsed row the check
reported was one added by hand earlier the same day, dated three weeks into the
past. Nothing else in the repo would have noticed.

Note what this does NOT cover, so a green run is not read as more than it is:
it checks that a human is not overdue on a row that EXISTS. A figure with no
register row at all is invisible here, and so is a row whose date is honoured
while the publisher has already issued a newer period.
"""
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TICK = "✅"
DATE_RE = re.compile(r"re-?read by (\d{4})-(\d{2})-(\d{2})")


def lapsed_rows(rows, today):
    """Rows whose re-read date is in the past, oldest first."""
    out = []
    for r in rows:
        if register.RECHECK not in r["mark"]:
            continue
        m = DATE_RE.search(r["mark"])
        if not m:
            continue
        due = datetime.date(*(int(g) for g in m.groups()))
        if due < today:
            out.append((due, r))
    return sorted(out, key=lambda t: t[0])


def main():
    rows = register.all_marked_rows()
    bad = [r for r in rows if TICK in r["mark"]]
    c = register.counts()
    print(f"=== MASTER_DATA.md: {len(rows)} marked rows ===\n")
    print(f"  written by a script   {c['script']}")
    print(f"  frozen, with a reason {c['frozen']}")
    print(f"  re-read by a date     {c['recheck']}")
    print(f"  bare hand tick        {c['hand']}")
    today = datetime.date.today()
    late = lapsed_rows(rows, today)

    if not bad and not late:
        print("\nNo row rests on a bare tick, and no re-read date has passed.")
        return 0

    if late:
        print(f"\nFAIL: {len(late)} row(s) are past their re-read date.\n",
              file=sys.stderr)
        for due, r in late[:40]:
            days = (today - due).days
            print(f"  due {due} ({days}d overdue)  "
                  f"[{r['section'].split('::')[0].strip()[:28]}] "
                  f"{r['label'][:60]}", file=sys.stderr)
        print("\nRe-read each one against its publisher, then move its date on "
              "by one publication cycle. Do NOT just push the date out: the "
              "date is the only thing standing between a figure and a year of "
              "nobody looking at it.\n", file=sys.stderr)

    if not bad:
        return 1
    print(f"\nFAIL: {len(bad)} row(s) carry a bare hand-verified tick.\n",
          file=sys.stderr)
    for r in bad[:40]:
        print(f"  [{r['section'][:30]}] {' | '.join(r['cells'][:3])[:90]}",
              file=sys.stderr)
    print("\nGive each one a mark that says how it is held up: wire it to the "
          "script that already fetches it, freeze it with the reason it "
          "cannot change, or set a re-read date from the publisher's cadence.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
