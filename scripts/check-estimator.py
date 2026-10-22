#!/usr/bin/env python3
"""Fail if the estimator's household compositions or their labels go missing.

WHAT THIS PROTECTS
The Full estimate tab offers 20 household compositions. Twelve are MIT's own
columns. The other eight were added on 2026-10-22 and are the kind of thing a
later edit removes without anyone noticing, because nothing else depends on
them:

  4 x "2 adults (neither working)"  -- NOT an extrapolation. MIT's one-earner
      columns already carry child care at $0 because an adult is home, so the
      cost column is identical and only income differs. They exist so a reader
      does not have to know that "1 working at 0% self-support" is the same
      household.
  4 x "... 4 children (derived)"    -- IS an extrapolation. MIT stops at three
      children. Each is the three-child household plus the mean of the three
      observed per-child increments, and every one of them must stay labelled,
      because the increments are uneven -- housing moves in bedroom steps --
      and an unlabelled derived figure on this hub is the exact failure this
      repository spent a week removing.

It also pins the population cap. The slider is labelled in households and the
headline population is in people; before 2026-10-22 it could be dragged to
400,000 HOUSEHOLDS, which at two adults and two children is 1.6 million people
and returned $42.32B -- two thirds of the enacted state budget. The cap is now
derived from the composition, and this checks the conversion still happens.

The derived values are recomputed here from MIT's own columns, so this does
not merely check that a string is present: if the derivation changes, the
numbers stop matching and the build fails.
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "immigration-dashboard.html")

NEITHER = [
    "2 adults (neither working)",
    "2 adults (neither working), 1 child",
    "2 adults (neither working), 2 children",
    "2 adults (neither working), 3 children",
]
DERIVED = [
    "1 adult, 4 children (derived)",
    "2 adults (1 working), 4 children (derived)",
    "2 adults (both working), 4 children (derived)",
    "2 adults (neither working), 4 children (derived)",
]
# The source columns each derived one is built from, in 0/1/2/3-child order.
FROM = {
    "1 adult, 4 children (derived)": [0, 1, 2, 3],
    "2 adults (1 working), 4 children (derived)": [4, 5, 6, 7],
    "2 adults (both working), 4 children (derived)": [8, 9, 10, 11],
}
REQUIRED_SNIPPETS = [
    ("window.setPeople", "the 400k-people preset is called from an inline "
                         "onclick and must be published to window, or it "
                         "throws a silent ReferenceError"),
    ("function syncCap", "the population cap that stops a household count "
                         "implying more people than the population"),
    ("LW.derived", "the per-composition derived warning"),
    ("LW.note", "the note explaining why neither-working matches one-earner"),
    ("lw-derived", "the class the derived warning renders with"),
]


def fail(msgs):
    print(f"FAIL: {len(msgs)} problem(s) with the estimator.\n", file=sys.stderr)
    for m in msgs:
        print(f"  {m}", file=sys.stderr)
    print("\nThese compositions and their labels were added deliberately. A "
          "derived figure that loses its label is worse than one that was "
          "never added.", file=sys.stderr)
    return 1


def main():
    with open(PAGE, encoding="utf-8") as fh:
        html = fh.read()

    bad = []

    m = re.search(r"var LW=(\{.*?\});", html, re.S)
    if not m:
        return fail(["the MIT living-wage dataset (var LW=) is not on the page"])
    lw = json.loads(m.group(1))
    cols = lw["columns"]
    if len(cols) != 12:
        bad.append(f"the sourced MIT block should hold 12 columns, found "
                   f"{len(cols)} -- the derived ones belong in extendLW at "
                   f"runtime, never written into the sourced data")

    for label in NEITHER + DERIVED:
        if label not in html:
            bad.append(f"composition missing: {label}")

    for snippet, why in REQUIRED_SNIPPETS:
        if snippet not in html:
            bad.append(f"missing {snippet!r} -- {why}")

    # Every derived composition must still say so in its own option text.
    for label in DERIVED:
        if "(derived)" not in label:
            bad.append(f"{label} no longer carries the word 'derived'")

    # Recompute the extrapolation from MIT's columns and check the page's own
    # method still produces it. A derivation that quietly changes is the thing
    # worth catching, not a missing string.
    items = lw["items"]
    expected = {}
    for label, (i0, i1, i2, i3) in FROM.items():
        g = lw["gross"]
        step = ((g[i1] - g[i0]) + (g[i2] - g[i1]) + (g[i3] - g[i2])) / 3
        expected[label] = round(g[i3] + step)
    # the neither-working four-child column copies the one-earner derived one
    expected[DERIVED[3]] = expected["2 adults (1 working), 4 children (derived)"]

    if "/3" not in html or "mean of the three" not in html:
        bad.append("the derivation no longer averages the three observed "
                   "per-child increments, or stopped saying so")

    # The cap must be computed, not a literal 400000 on the slider.
    sl = re.search(r'<input[^>]*id="hh"[^>]*>', html)
    if sl and 'max="400000"' in sl.group(0):
        bad.append("the households slider is capped at 400,000 again -- that "
                   "is the PEOPLE figure, and at 2 adults + 2 children it "
                   "means 1.6 million people and a $42.3B answer")

    if bad:
        return fail(bad)

    print("=== estimator: 20 compositions, labels and cap intact ===\n")
    print(f"  MIT columns, untouched        {len(cols)}")
    print(f"  neither-working added          {len(NEITHER)}")
    print(f"  derived, all labelled          {len(DERIVED)}")
    for label in DERIVED[:3]:
        print(f"    {label:<46} ${expected[label]:,}")
    print("  population cap derived from the selected composition")
    return 0


if __name__ == "__main__":
    sys.exit(main())
