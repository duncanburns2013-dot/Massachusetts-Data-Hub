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
# The figures this script prints are the ones off the page, so they carry the
# page's typography -- U+2212 MINUS SIGN among it. On Windows the default console
# encoding is cp1252, which cannot encode it, so printing the report raised
# UnicodeEncodeError and the script exited 1 with its real verdict ("No new
# unaccountable figures") already on screen above the traceback. The weekly local
# health check read that as a failed gate. Same idiom as pdftext.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
    """The comparable core of a printed statistic.

    HTML entities are stripped FIRST. Without that, the numeric escape in a
    currency or unit symbol leaks into the comparison: "30.49&#x00A2;" (the cent
    sign) reduced to "30.49002", which can never match the "30.49" written in
    method.html. Every cent-denominated figure on the energy dashboard was
    therefore permanently unverifiable by this check -- it reported them as
    undocumented no matter what MASTER_DATA.md said. Found 2026-10-01, when the
    EIA release moved the values and made the breakage visible.
    """
    text = re.sub(r"&#?\w+;", "", text)
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


FROZEN = re.compile(r'data-frozen="([^"]{8,})"')
# A figure can also be owned by a markup-anchored regex substitution rather than
# by a data-field. update-energy-dashboard.py works that way throughout -- 31
# labelled substitutions that match on surrounding markup and rewrite the value
# in place -- so its figures ARE script-written, and this check could not see it.
# "+76%" on the annual-average card is written by substitution 17 every run, and
# was being reported as unaccountable anyway.
#
# Adding a data-field there is not free: those regexes match the value element's
# own tag, so a new attribute on it breaks the writer. data-owned-by goes on the
# CARD instead, naming the script, which no substitution matches against.
OWNED_BY = re.compile(r'data-owned-by="([a-z0-9_.-]+\.py)"')


def scan(collect_frozen=None):
    """Every headline statistic that is neither anchored, frozen, nor documented.

    THREE ways a figure can be accounted for, and the third was missing:

      anchored    carries id= or data-field=, so an updater writes it
      documented  its digits appear in method.html
      FROZEN      carries data-frozen="<why>", declaring it a point-in-time
                  claim that must NOT track the newest release

    Without the third, this check could not tell a deliberate vintage from a
    forgotten number, and both sat in the same undifferentiated backlog. They
    want opposite treatment. "+8,500 -- as first reported, since revised to
    +7,400" is CORRECT precisely because it does not move; wiring it to a feed
    would destroy the claim. "105.8 BEA Cost of Living" was simply unwired.
    Lumping them together meant the real backlog could never be driven to zero,
    so nobody tried.

    data-frozen takes a reason of at least 8 characters, because "frozen" with
    no stated why is how a stale figure gets relabelled instead of fixed. The
    reason is on the page, next to the figure, where the next reader finds it.
    """
    documented = method_numbers()
    found = []
    for f in sorted(REPO.glob("*.html")):
        if f.name in SKIP:
            continue
        html = f.read_text(encoding="utf-8")
        for card in CARD.finditer(html):
            block = card.group(1)
            # The whole match, opening tag included. CARD's capture group starts
            # AFTER the card's own tag, so a data-frozen or data-owned-by placed
            # on the card element itself is invisible to `block` -- and the card
            # is exactly where data-owned-by has to go, since the writers' regexes
            # match the value element's tag and a new attribute there breaks them.
            whole = card.group(0)
            v = VALUE.search(block)
            if not v:
                continue
            attrs, inner = v.group(1), v.group(2)
            raw = TAG.sub("", inner).replace("&mdash;", "").strip()
            d = digits(raw)
            if not d or len(d) < 2:      # single digits are noise, not claims
                continue
            anchored = ("id=" in attrs or "data-field=" in attrs
                        or "data-field=" in block or "data-mig=" in block)
            frozen = FROZEN.search(whole)
            owned_by = OWNED_BY.search(whole)
            if frozen and collect_frozen is not None:
                collect_frozen.append({"page": f.name, "value": raw[:24],
                                       "why": frozen.group(1)})
            # A RANGE is documented when both its endpoints are. digits()
            # collapses "$135-225M" to "135225", which method_numbers() can
            # never produce: it reads numbers one at a time, so the same figure
            # appears there as "135" and "225". Without this, a range is
            # permanently unaccountable no matter how well it is documented --
            # which is what happened to the SNAP fraud estimate after it was
            # written into MASTER_DATA.md with its Auditor and USDA sources.
            parts = [digits(x) for x in re.split(r'[–—-]', raw)]
            parts = [x for x in parts if x and len(x) >= 2]
            ranged = len(parts) > 1 and all(x in documented for x in parts)

            if anchored or frozen or owned_by or d in documented or ranged:
                continue
            label = re.sub(r"\s+", " ", TAG.sub(" ", block[v.end():])).strip()[:60]
            found.append({"page": f.name, "value": raw[:24], "label": label})
    return found


def key(item):
    return "%s|%s" % (item["page"], item["value"])


def main():
    frozen = []
    found = scan(collect_frozen=frozen)
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

    # Frozen figures are accounted for, not invisible. A declaration that is
    # never shown again is how a figure gets quietly relabelled instead of
    # fixed, so every one is listed with the reason it carries, for a human to
    # disagree with.
    if frozen:
        print()
        print("%d frozen as point-in-time claims (must NOT track the newest "
              "release):" % len({(f["page"], f["value"]) for f in frozen}))
        for f in sorted({(f["page"], f["value"], f["why"]) for f in frozen}):
            print("   %-28s %-14s %s" % (f[0], f[1], f[2]))

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
