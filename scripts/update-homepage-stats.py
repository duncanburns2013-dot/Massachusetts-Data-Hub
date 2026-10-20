#!/usr/bin/env python3
"""Write the homepage's "Last refreshed" and "Live data feeds" figures.

WHY THIS EXISTS
index.html carried `Last refreshed  18 Aug 2026` as a hand-typed literal under a
label reading "Computed at runtime from official sources". Nothing computed it.
`turn-dash` beside it IS set by JS at runtime; this one never was, so it froze on
the day someone typed it and then aged in public for 63 days.

That is the worst shape a staleness bug can take. Every feed was current -- MLS,
NH and employment had all committed within the previous 24 hours -- but the first
thing a reader saw on the front page was a two-month-old date presented as live.
The site looked abandoned while working perfectly, and no check could see it:
check-freshness.py ages the figures a page publishes, and this was a figure ABOUT
the publishing.

WHAT IT WRITES
  hub-updated  the newest commit date touching data/ -- the honest answer to
               "when did the data last change", and the same measure
               check-freshness.py ages every feed by.
  hub-feeds    how many registered sources a workflow actually fetches, counted
               from check-freshness.py's own DATA register so the two can never
               disagree. Entries the register marks as unfetchable by any
               workflow (the SoC lobbying scrape) are excluded -- calling a
               by-hand browser scrape a live feed would be the same lie in a
               smaller font.

Run daily by rebuild-generated.yml. index.html's stamp is registered in
check-freshness.py, so if this ever stops the watchdog says so instead of the
front page quietly rotting again.
"""
import datetime
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAGE = REPO / "index.html"


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def newest_data_commit():
    """Date of the most recent commit touching data/."""
    out = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", "data/"],
        cwd=REPO, capture_output=True, text=True,
    )
    if out.returncode != 0 or not out.stdout.strip():
        fail("git log gave no commit for data/ -- is this a shallow clone? "
             "This job needs fetch-depth: 0.")
    return datetime.date.fromisoformat(out.stdout.strip())


def fetched_feed_count():
    """Registered sources a workflow can actually fetch, per the register itself."""
    reg = REPO / "scripts" / "check-freshness.py"
    spec = importlib.util.spec_from_file_location("_freshness", reg)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data = getattr(mod, "DATA", None)
    if not data:
        fail("could not read DATA out of check-freshness.py")
    # The register documents an unfetchable source in its own note. Honour that
    # rather than keeping a second list here that would drift out of step.
    return sum(1 for _path, _days, note in data if "no workflow" not in note.lower())


def setf(html, tag, value):
    new, n = re.subn(r'(data-field="' + re.escape(tag) + r'">)[^<]*(<)',
                     lambda m: m.group(1) + value + m.group(2), html, count=1)
    if n == 0:
        fail(f'data-field="{tag}" is missing from index.html. Nothing written.')
    return new


def main():
    print("=== homepage stats ===\n")

    when = newest_data_commit()
    feeds = fetched_feed_count()
    # Match the typed form that was there: "18 Aug 2026", no zero padding.
    stamp = f"{when.day} {when:%b %Y}"

    age = (datetime.date.today() - when).days
    print(f"  newest data/ commit   {when}  ({age}d ago)")
    print(f"  fetched feeds         {feeds}")

    html = PAGE.read_text(encoding="utf-8")
    before = html
    html = setf(html, "hub-updated", stamp)
    html = setf(html, "hub-feeds", str(feeds))

    if html == before:
        print("\nNo changes - homepage already current.")
        return

    PAGE.write_text(html, encoding="utf-8")
    print(f"\n  wrote index.html: last refreshed {stamp}, {feeds} live feeds")


if __name__ == "__main__":
    main()
