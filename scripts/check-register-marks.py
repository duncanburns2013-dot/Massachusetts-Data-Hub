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
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TICK = "✅"
DATE_RE = re.compile(r"re-?read by (\d{4})-(\d{2})-(\d{2})")
SCRIPT_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|js|mjs|yml))`")
# A section may attribute a row to a FEED rather than a script -- the
# concentration-city subsection opens "Live values: `data/census-latest.json`".
# That is attribution a reader can follow, and since 2026-11-22 those rows are
# compared with that feed by check-consistency.py every run, so the claim is
# enforced rather than asserted.
OWNER_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|js|mjs|yml|json))`")
REPO = pathlib.Path(__file__).resolve().parents[1]
REGISTER_LINES = (REPO / "MASTER_DATA.md").read_text(encoding="utf-8").split(chr(10))


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


def undated_rows(rows):
    """Hourglass rows that name no date at all, added 2026-11-22.

    The hourglass means "a human re-reads this, and here is when they are next
    due". Six rows carried the first half and not the second:

      | Government jobs, MA        | ... | <hourglass> re-read monthly; preliminary until revised |
      | MassHealth members         | ... | <hourglass> re-read monthly, the next snapshot |
      | Public money, total        | ... | <hourglass> moves with the rows above |
      | Inflation                  | ... | <hourglass> re-read annually once the fiscal year closes |

    Every one states a cadence. None states a deadline, so no date could pass
    and nothing could ever ring -- the lapse check added earlier the same day
    skipped them on `if not m: continue`, and check-freshness.py skipped them
    too. "Re-read monthly" with no month is the bare tick this file was written
    to abolish, wearing a longer sentence.

    Five of the six were MONTHLY figures, which is the worst place for it: the
    most volatile numbers on the site had the weakest mark on it. All six held
    correct values when this was found, which is the point -- nothing was wrong
    yet, and nothing would have said so when it was.
    """
    return [r for r in rows
            if register.RECHECK in r["mark"] and not DATE_RE.search(r["mark"])]



def phantom_scripts(rows):
    """Script marks that name a file which is not in the repo, added 2026-11-22.

    A row marked with the script glyph says "a job writes this, you do not have
    to". Naming the job is what makes that checkable, and the name was never
    checked against the filesystem.

    The US job openings row said:

      | US job openings | 7.523M | September 2026 | BLS JOLTS <script> written
        by `update-employment.py`; checked by check-consistency.py |

    There is no update-employment.py, and there never was. The figure IS written
    -- by scripts/fetch-bls-data.js, which update-employment.yml runs as
    `node fetch-bls-data.js` -- so the row was right about being owned and wrong
    about by what, which is the version of this that survives a reading.

    Scripts live in two places here, the repo root and scripts/, and a mark may
    give either a bare name or a path. Both resolve. A workflow file counts too.
    """
    out = []
    for r in rows:
        if register.SCRIPT not in r["mark"]:
            continue
        for name in SCRIPT_RE.findall(r["mark"]):
            base = name.split("/")[-1]
            if any((REPO / p / base).exists()
                   for p in ("", "scripts", ".github/workflows")):
                continue
            out.append((name, r))
    return out



def unnamed_scripts(rows):
    """Script marks that name no script, added 2026-11-22. A WARNING, not a fail.

    The glyph says "a job writes this, you do not have to". Naming the job is
    what makes that checkable. 40 rows carry the glyph and name nothing: a month
    ("<glyph> Jul 2026"), a source ("BLS LAUS <glyph>"), or the glyph alone.

    Some are simply unlabelled and fine -- the writer exists, nobody wrote it
    down. Others are false: update-census-data.py writes pages and a feed and
    never touches this file, so the fourteen immigrant-concentration city rows
    claim a register write that does not happen. Telling those two apart takes
    reading the script, one row at a time, and guessing is exactly how
    "update-employment.py" came to be named for a file that never existed.

    So this reports rather than fails. The number should fall and must never
    quietly rise, the way stat-baseline.json works. Failing today would turn CI
    red on a backlog nobody chose, and the rows are not wrong about being owned
    -- most of them are just silent about by what.
    """
    # Attribution here is often made at SECTION level, not per row: the Energy
    # heading says "Refreshed by `update-energy-dashboard.py` and
    # `update-fuel-prices.py`", and the MLS subsection opens with "Source of
    # truth: `data/mls-history.json`". A row under either IS checkable by
    # reading, so counting it as unnamed would nag about a convention the file
    # actually keeps. Scan back to the nearest heading and accept a script
    # named anywhere in between.
    out = []
    for r in rows:
        if register.SCRIPT not in r["mark"]:
            continue
        if SCRIPT_RE.search(r["mark"]):
            continue
        try:
            at = int(r["i"])
        except (KeyError, TypeError, ValueError):
            out.append(r)
            continue
        top = at
        while top > 0 and not REGISTER_LINES[top].lstrip().startswith("#"):
            top -= 1
        if OWNER_RE.search(chr(10).join(REGISTER_LINES[top:at])):
            continue
        out.append(r)
    return out



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
    undated = undated_rows(rows)
    phantom = phantom_scripts(rows)
    unnamed = unnamed_scripts(rows)

    # Not a failure. See unnamed_scripts above for why.
    if unnamed:
        print()
        print("%d row(s) carry the script glyph and name neither a script nor a feed "
              "(not a failure -- but" % len(unnamed))
        print("   the claim that a job owns them cannot be checked by reading "
              "them):")
        import collections as _c
        for sec, n in _c.Counter(
                r["section"].split("::")[0].strip()[:34] for r in unnamed
        ).most_common():
            print("   %-36s %d" % (sec, n))

    if not bad and not late and not undated and not phantom:
        print("\nNo row rests on a bare tick, every re-read date is in "
              "the future, and every hourglass names one.")
        return 0

    if phantom:
        print("\nFAIL: %d script mark(s) name a file that is not in the repo."
              % len(phantom), file=sys.stderr)
        print(file=sys.stderr)
        for name, r in phantom:
            print("  `%s`  --  %s" % (name, r["label"][:54]), file=sys.stderr)
        print("\nThe row claims a job owns the figure. Name the job that "
              "actually does, or give the row a re-read date instead. A mark "
              "naming a script nobody can open is the same bare tick in "
              "different clothing.", file=sys.stderr)
        print(file=sys.stderr)

    if undated:
        print(f"\nFAIL: {len(undated)} hourglass row(s) name no re-read date.\n",
              file=sys.stderr)
        for r in undated:
            print(f"  [{r['section'].split('::')[0].strip()[:26]}] "
                  f"{r['label'][:46]}", file=sys.stderr)
            print(f"      mark: {r['mark'][:88]}", file=sys.stderr)
        print("\nA cadence is not a deadline. Give each one 're-read by "
              "<YYYY-MM-DD>' from the publisher's own schedule -- and re-read "
              "it NOW before setting that date, rather than dating a figure "
              "nobody has looked at.\n", file=sys.stderr)


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
