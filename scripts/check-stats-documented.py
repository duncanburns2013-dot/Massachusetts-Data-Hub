#!/usr/bin/env python3
"""Fail when a NEW headline statistic appears that nobody can check.

WHY THIS EXISTS
The immigration page showed "137K -- MA Residents Left" for a year. No script
wrote it, Method had no row for it, and the freshness watchdog could not see it
because the watchdog only ages sources that are registered with it. Census
published a new vintage, restated the series, and the card stayed where it was
until a Boston Herald piece quoted the current figure -- 182,000 -- back at us.
A reader found it. On a site whose argument is that every figure is checkable,
that is the failure that matters most.

THE RULE
A headline statistic must be one of:
  * script-written -- the element carries an id or a data-field anchor, so some
    updater owns the value and it moves when the data moves; or
  * documented    -- the number appears in method.html, so a reader can trace it.

A number that is neither is a claim maintained by memory.

WHY NOT A BROWSER
An earlier version of this check rendered the pages, which was slow and needed
Chrome in CI. It is unnecessary: the two cases that matter are distinguishable
statically. Merrimack Valley's hero cards look empty in the HTML because JS
fills them -- but they carry ids, so the anchor rule passes them. The
immigration figure was bare text in a div, so the same rule flags it. Reading
the DOM added cost and no signal.

RATCHET, NOT A CLIFF
143 statistics do not meet the rule today. Failing the build on all of them
would mean turning the check off, so the current set is recorded in
stat-baseline.json and the build fails only on something NEW. The baseline is
meant to shrink; it must never grow silently.

  python scripts/check-stats-documented.py            # check
  python scripts/check-stats-documented.py --update   # re-record the baseline
"""
import io
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASELINE = Path(__file__).resolve().parent / "stat-baseline.json"

SKIP = {"template.html", "404.html", "method.html", "instrument.html"}

# a headline value: the value element inside a headline card
CARD = re.compile(
    r'<div[^>]*class="[^"]*\b(?:stat-box|stat-card|kpi|hero-stat)\b[^"]*"[^>]*>(.{0,900}?)</div>\s*</div>',
    re.S)
VALUE = re.compile(
    r'<div[^>]*class="[^"]*\b(?:num|val|stat-value|kpi-num|value)\b[^"]*"([^>]*)>(.*?)</div>',
    re.S)
TAG = re.compile(r"<[^>]+>")


def digits(text):
    """The comparable core of a printed statistic."""
    d = re.sub(r"[^0-9.]", "", text)
    d = d.rstrip(".").lstrip("0")
    return d or None


def method_numbers():
    p = REPO / "method.html"
    if not p.exists():
        return set()
    text = TAG.sub(" ", p.read_text(encoding="utf-8"))
    out = {digits(x) for x in re.findall(r"[\d][\d,]*\.?\d*", text)}
    out.discard(None)
    return out


def scan():
    """Every headline statistic that is neither anchored nor documented."""
    documented = method_numbers()
    found = []
    for f in sorted(REPO.glob("*.html")):
        if f.name in SKIP:
            continue
        html = f.read_text(encoding="utf-8")
        for card in CARD.finditer(html):
            block = card.group(1)
            v = VALUE.search(block)
            if not v:
                continue
            attrs, inner = v.group(1), v.group(2)
            raw = TAG.sub("", inner).replace("&mdash;", "").strip()
            d = digits(raw)
            if not d or len(d) < 2:      # single digits are noise, not claims
                continue
            anchored = ("id=" in attrs or "data-field=" in attrs
                        or "data-field=" in block)
            if anchored or d in documented:
                continue
            label = re.sub(r"\s+", " ", TAG.sub(" ", block[v.end():])).strip()[:60]
            found.append({"page": f.name, "value": raw[:24], "label": label})
    return found


def key(item):
    return "%s|%s" % (item["page"], item["value"])


def main():
    found = scan()
    update = "--update" in sys.argv

    if update:
        BASELINE.write_text(
            json.dumps({"known": sorted({key(i) for i in found}),
                        "note": "Statistics that are neither script-written nor in "
                                "method.html. This list should shrink, never grow. "
                                "Regenerate with --update only when removing entries."},
                       indent=1) + "\n", encoding="utf-8")
        print("baseline re-recorded: %d undocumented statistics" % len(found))
        return 0

    known = set()
    if BASELINE.exists():
        known = set(json.loads(BASELINE.read_text(encoding="utf-8")).get("known", []))

    # Compared as a set of page|value keys: the same figure can be printed in
    # more than one card on a page, and counting those separately would make the
    # totals disagree with the baseline for no useful reason.
    seen, new = set(), []
    for i in found:
        k = key(i)
        if k in seen:
            continue
        seen.add(k)
        if k not in known:
            new.append(i)
    fixed = known - seen

    print("headline statistics that are neither script-written nor documented")
    print("  in the baseline : %d" % len(known))
    print("  found now       : %d" % len(seen))
    print("  newly appeared  : %d" % len(new))
    print("  since documented: %d" % len(fixed))

    if fixed:
        print()
        print("%d baseline entries are now accounted for. Re-record with --update "
              "so they cannot come back unnoticed:" % len(fixed))
        for k in sorted(fixed)[:12]:
            print("   " + k)

    if new:
        print()
        print("NEW undocumented statistics -- each needs either an updater that writes")
        print("it (an id or data-field anchor) or a row in MASTER_DATA.md:")
        for i in new:
            print("   %-30s %-14s %s" % (i["page"], i["value"], i["label"]))
        return 1

    print()
    print("No new unaccountable figures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
