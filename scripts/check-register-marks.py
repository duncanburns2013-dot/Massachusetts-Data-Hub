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
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TICK = "✅"


def main():
    rows = register.all_marked_rows()
    bad = [r for r in rows if TICK in r["mark"]]
    c = register.counts()
    print(f"=== MASTER_DATA.md: {len(rows)} marked rows ===\n")
    print(f"  written by a script   {c['script']}")
    print(f"  frozen, with a reason {c['frozen']}")
    print(f"  re-read by a date     {c['recheck']}")
    print(f"  bare hand tick        {c['hand']}")
    if not bad:
        print("\nNo row rests on a bare tick.")
        return 0
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
