#!/usr/bin/env python3
"""Fail the build if a figure that was corrected once comes back.

WHY THIS EXISTS
Three gates already run here and none of them catches this:

  check-stats-documented.py  a hero figure on a page that no script owns
  check-consistency.py       MASTER_DATA.md drifting from a feed it registers
  check-freshness.py         a feed that has stopped updating

What none of them catch is a figure that was already found wrong, corrected in
one place, and left standing in another. That is how HomeBASE's FY2026 spending
was corrected on 2026-09-30 and was still published at the old value on the
immigration dashboard, in MASTER_DATA.md and in method.html on 2026-10-21 --
three weeks, three pages, and it was a person reading the site who noticed,
not a check.

HOW IT WORKS
data/retired-figures.json lists each retired value with a context regex. A hit
counts only when the context appears within context_window characters of the
value, so "252%" in an unrelated chart does not fail the build but "252%" next
to the word HomeBASE does. Nothing here is fuzzy: an entry names the exact
written forms to look for.

Exit 0 clean, exit 1 on any live retired figure.
"""
import fnmatch
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "data", "retired-figures.json")

# Wrap a published correction note in these and the figures it quotes are not
# treated as live claims:
#
#   <!--retired-quote-->This read "$87,548", which counted salaries
#   only...<!--/retired-quote-->
#
# Comment delimiters rather than a class attribute, so the same convention
# works in Markdown and in HTML, and so no tag nesting has to be parsed.
QUOTE = re.compile(r"<!--\s*retired-quote\s*-->.*?<!--\s*/\s*retired-quote\s*-->",
                   re.S)


def candidate_files(spec):
    pats = spec["scan"]["files"]
    skip = set(spec["scan"]["skip_dirs"])
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = os.path.relpath(dirpath, ROOT).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        dirnames[:] = [d for d in dirnames
                       if d not in skip
                       and not d.startswith(".")
                       and (f"{rel_dir}/{d}" if rel_dir else d) not in skip]
        for fn in filenames:
            rel = (f"{rel_dir}/{fn}" if rel_dir else fn)
            if any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(fn, p)
                   for p in pats):
                out.append(rel)
    return sorted(out)


def read_scannable(rel, spec):
    """File text, truncated where the spec says a history section begins.

    MASTER_DATA.md's update log names every figure it ever corrected -- that is
    what an update log is for. Scanning it would mean the act of recording a
    correction fails the build.
    """
    path = os.path.join(ROOT, rel)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    cut = spec["scan"].get("skip_after_heading", {}).get(rel)
    if cut and cut in text:
        text = text.split(cut, 1)[0]
    # A page that tells the reader what it used to say has to name the old
    # figure, and that sentence is the opposite of the problem -- it is the
    # correction being shown rather than hidden. Wrapping it in these markers
    # takes it out of the scan, for every entry at once. Newlines are kept so
    # reported line numbers stay right.
    text = QUOTE.sub(lambda mt: "\n" * mt.group(0).count("\n"), text)
    return text


def main():
    with open(SPEC, encoding="utf-8") as fh:
        spec = json.load(fh)
    entries = spec["retired"]
    files = candidate_files(spec)
    print(f"=== retired figures: {len(entries)} entries against "
          f"{len(files)} files ===\n")

    hits = []
    for rel in files:
        text = read_scannable(rel, spec)
        if text is None:
            continue
        for e in entries:
            if rel in e.get("allow", []):
                continue
            ctx = re.compile(e["context"])
            win = int(e.get("context_window", 200))
            for bad in e["wrong"]:
                for mt in re.finditer(re.escape(bad), text):
                    lo = max(0, mt.start() - win)
                    hi = min(len(text), mt.end() + win)
                    around = text[lo:hi]
                    if not ctx.search(around):
                        continue
                    line = text.count("\n", 0, mt.start()) + 1
                    snippet = re.sub(r"\s+", " ", around).strip()
                    if len(snippet) > 180:
                        half = 86
                        off = mt.start() - lo
                        snippet = "..." + re.sub(
                            r"\s+", " ",
                            around[max(0, off - half):off + half]).strip() + "..."
                    hits.append({
                        "file": rel, "line": line, "id": e["id"],
                        "bad": bad, "right": e["right"], "why": e["why"],
                        "snippet": snippet,
                    })

    if not hits:
        print("No retired figure is live. Clean.")
        for e in entries:
            print(f"  watched  {e['id']:<28} {', '.join(e['wrong'])[:60]}")
        return 0

    # One line per place, grouped by figure, because a figure that came back
    # usually came back in more than one place at once.
    by_id = {}
    for h in hits:
        by_id.setdefault(h["id"], []).append(h)
    print(f"FAIL: {len(hits)} live instance(s) of "
          f"{len(by_id)} retired figure(s).\n")
    for fid, group in by_id.items():
        e = next(x for x in entries if x["id"] == fid)
        print(f"  {fid}  ({e['subject']})")
        print(f"    should be: {e['right']}")
        print(f"    retired because: {e['why']}")
        for h in group:
            print(f"      {h['file']}:{h['line']}  found \"{h['bad']}\"")
            print(f"        {h['snippet']}")
        print()
    print("Correct the figure, or -- if this use is legitimate -- add the file "
          "to that entry's \"allow\" list in data/retired-figures.json with a "
          "note saying why.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
