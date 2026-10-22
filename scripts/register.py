#!/usr/bin/env python3
"""Write rows into MASTER_DATA.md, keyed on the row label.

WHY THIS IS SHARED
Four updaters had each grown their own way of editing the register and the
other six did not touch it at all -- they fetched the data, stamped the page,
and left the register row to a human. That is how 166 rows came to carry a
hand-verified tick: not because anyone decided they should be hand-kept, but
because wiring each script to the register was work nobody had done.

THE MARKS, AND WHAT THEY PROMISE
  (script)  a job writes this row. The value is whatever the source said on
            the last successful run.
  (frozen)  this cannot change. A recorded roll call, a signed act, a statute,
            a closed fiscal year's published total. It carries the reason, and
            it is NOT re-checked because there is nothing to re-check.
  (recheck) no API, so a human reads it -- a quarterly broker report, a
            subscription dataset. It carries a due date, and check-freshness.py
            ages it so a forgotten one fails instead of sitting.

A hand-verified tick with a date is the fourth state and the one being removed.
It looks identical to (script) on the page and promises the same thing, and it
was on the HomeBASE row that was wrong for six weeks.

Matching is on the row's first cell, exactly. Nothing here regexes prose.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, "MASTER_DATA.md")

SCRIPT = "\U0001f504"     # the register's existing "refreshed by a feed" mark
FROZEN = "\U0001f512"     # padlock
RECHECK = "⏳"        # hourglass


def _cells(line, width=4):
    """Cells of a table row, or None.

    width=4 is the common shape (metric | value | source | mark) and is what
    write_rows edits. Pass width=None for ANY shape: the register also has
    3-, 5- and 6-column tables -- median prices carry a change column, the
    rate-increase tables carry a carrier column -- and the status mark is
    always the LAST cell. Counting only 4-column rows is how an audit of
    "166 hand-verified rows" missed a further 100 of them.
    """
    if not line.startswith("|"):
        return None
    c = [x.strip() for x in line.strip("|").split("|")]
    if width is None:
        return c if 2 <= len(c) <= 8 else None
    return c if len(c) == width else None


def _log_start(lines):
    for i, l in enumerate(lines):
        if l.startswith("## ") and "Update Log" in l:
            return i
    return len(lines)


def _section_of(lines):
    """Line index -> the '## ' heading it falls under.

    Labels are NOT unique in this file. "FY2022" is a row in Immigration (a
    CBP encounter total), in Cost of Living (a BSI recovery total) and in
    State Budget (a GAA appropriation). Matching on the label alone would
    write a budget figure over an immigration one and report success, which is
    the exact class of silent mis-targeting this whole pass exists to remove.
    Every write is therefore scoped to a section.
    """
    out, cur, sub = {}, "(top)", ""
    for i, l in enumerate(lines):
        # '###' must be tested first: it also startswith('## ').
        if l.startswith("### "):
            sub = re.sub(r"[^\x20-\x7e]", "", l[4:]).strip()
        elif l.startswith("## "):
            cur = re.sub(r"[^\x20-\x7e]", "", l[3:]).strip()
            sub = ""
        # Both levels are searchable, because two tables under ONE heading can
        # carry identical labels -- the national and Massachusetts BLS release
        # schedules are each a list of the same months.
        out[i] = f"{cur} :: {sub}" if sub else cur
    return out


def _match(lines, i, label, section, secmap):
    c = _cells(lines[i])
    if not c or c[0] != label:
        return False
    if section is None:
        return True
    return section.lower() in secmap.get(i, "").lower()


def read_rows():
    """Every register row above the update log, as dicts."""
    with open(REGISTER, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    out = []
    for i, l in enumerate(lines[: _log_start(lines)]):
        c = _cells(l)
        if not c or c[0] in ("Metric", "") or set(c[1]) <= set("- "):
            continue
        out.append({"i": i, "metric": c[0], "value": c[1],
                    "source": c[2], "verified": c[3]})
    return out


def write_rows(updates, owner, source=None, section=None, dry_run=False):
    """Set value/source/mark on existing rows, keyed on the exact label.

    updates: {label: value} or {label: (value, source)}
    owner:   the script filename, e.g. "update-mcas.py"
    section: restrict to rows under a '## ' heading containing this text.
             Pass it whenever a label might not be unique -- see _section_of.

    Returns (written, missing). A label that is not in the register is
    REPORTED, never inserted blind -- a row appearing in a section it does not
    belong to is worse than a row that is still hand-kept, and the caller
    knows where its rows live.
    """
    with open(REGISTER, encoding="utf-8") as fh:
        text = fh.read()
    lines = text.split("\n")
    stop = _log_start(lines)
    secmap = _section_of(lines)
    mark = f"{SCRIPT} written by `{owner}`"
    written, seen = [], set()
    for i in range(stop):
        c = _cells(lines[i])
        if not c:
            continue
        label = c[0]
        if label not in updates or label in seen:
            continue
        if not _match(lines, i, label, section, secmap):
            continue
        val = updates[label]
        src = source or c[2]
        if isinstance(val, (tuple, list)):
            val, src = val[0], (val[1] or src)
        lines[i] = f"| {label} | {val} | {src} | {mark} |"
        seen.add(label)
        written.append(label)
    missing = [k for k in updates if k not in seen]
    if not dry_run and written:
        with open(REGISTER, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    return written, missing


def freeze_rows(reasons, section=None, dry_run=False):
    """Mark rows that cannot change, each with why.

    reasons: {label: "why it cannot change"}
    """
    with open(REGISTER, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    stop = _log_start(lines)
    secmap = _section_of(lines)
    done, seen = [], set()
    for i in range(stop):
        c = _cells(lines[i])
        if not c:
            continue
        if c[0] not in reasons or c[0] in seen:
            continue
        if not _match(lines, i, c[0], section, secmap):
            continue
        why = reasons[c[0]]
        lines[i] = f"| {c[0]} | {c[1]} | {c[2]} | {FROZEN} {why} |"
        seen.add(c[0])
        done.append(c[0])
    if not dry_run and done:
        with open(REGISTER, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    return done, [k for k in reasons if k not in seen]


def recheck_rows(due, section=None, dry_run=False):
    """Mark rows a human must re-read, with the date they are due.

    due: {label: ("YYYY-MM-DD", "what to re-read")}
    """
    with open(REGISTER, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    stop = _log_start(lines)
    secmap = _section_of(lines)
    done, seen = [], set()
    for i in range(stop):
        c = _cells(lines[i])
        if not c:
            continue
        if c[0] not in due or c[0] in seen:
            continue
        if not _match(lines, i, c[0], section, secmap):
            continue
        when, what = due[c[0]]
        lines[i] = (f"| {c[0]} | {c[1]} | {c[2]} | "
                    f"{RECHECK} re-read by {when} — {what} |")
        seen.add(c[0])
        done.append(c[0])
    if not dry_run and done:
        with open(REGISTER, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    return done, [k for k in due if k not in seen]


def all_marked_rows():
    """Every row of any shape, with its last cell -- where the mark lives."""
    with open(REGISTER, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    secmap = _section_of(lines)
    out = []
    for i, l in enumerate(lines[: _log_start(lines)]):
        c = _cells(l, width=None)
        if not c or len(c) < 3:
            continue
        if c[0] in ("Metric", "") or set("".join(c)) <= set("- :"):
            continue
        out.append({"i": i, "label": c[0], "cells": c, "mark": c[-1],
                    "section": secmap[i], "width": len(c)})
    return out


def mark_rows(decide, section=None, dry_run=False):
    """Set the LAST cell of matching rows, whatever the table's width.

    decide(row) -> replacement mark string, or None to leave the row alone.
    row is a dict from all_marked_rows().

    freeze_rows/recheck_rows above take an explicit {label: reason} map and
    only touch 4-column tables. This is for the register's other shapes --
    the tax tables carry a URL column, the rate tables have three columns --
    where the rows are numerous and follow a rule rather than needing to be
    named one at a time.
    """
    with open(REGISTER, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    secmap = _section_of(lines)
    done = []
    for r in all_marked_rows():
        i = r["i"]
        if section and section.lower() not in secmap.get(i, "").lower():
            continue
        new = decide(r)
        if not new:
            continue
        cells = list(r["cells"])
        cells[-1] = new
        lines[i] = "| " + " | ".join(cells) + " |"
        done.append(r["label"])
    if not dry_run and done:
        with open(REGISTER, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    return done


def counts():
    """How the register is held up, by mark. Every table shape, not just 4."""
    out = {"script": 0, "frozen": 0, "recheck": 0, "hand": 0, "other": 0}
    for r in all_marked_rows():
        v = r["mark"]
        if SCRIPT in v:
            out["script"] += 1
        elif FROZEN in v:
            out["frozen"] += 1
        elif RECHECK in v:
            out["recheck"] += 1
        elif "✅" in v:
            out["hand"] += 1
        else:
            out["other"] += 1
    return out


if __name__ == "__main__":
    import json
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(counts(), indent=1))
