#!/usr/bin/env python3
"""Fail when two pages publish different values for the same named quantity.

WHY
HomeBASE's FY2026 spending was published at $91.35M on one page and $57.29M on
another for three weeks. Every other gate here was green and correct: the feed
was fresh, the figure was documented in the register, and the register row that
check-consistency watches was not that row. The contradiction was only visible
by holding the two pages side by side, and nothing did that.

This does. It is the check that would have caught it.

HOW A VALUE IS BOUND TO A NAME
Two bindings, both structural -- never proximity. Proximity was tried first and
reported every figure in a table as belonging to whatever subject appeared
nearby, which is noise, not signal.

  table cell   bound to its row label AND its column header, so
               "HomeBASE x FY2026" is one key and "HomeBASE x FY2027" another.
               Binding to the row alone was the noise in the first attempt: it
               made every year of a series look like a disagreement.
  card         a leaf element whose whole text is a figure, bound to the
               adjacent leaf element that is words.

$1.85B, $1,850M and $1,850,000,000 are the same claim, so values are compared
as numbers in millions, with 1.5% of slack for honest rounding.

BASELINE
scripts/cross-page-baseline.json records differences already looked at and
accepted -- the same pattern check-stats-documented.py uses. The list should
shrink. A NEW divergence fails the build; an accepted one does not.
"""
import html as htmlmod
import json
import os
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, "scripts", "cross-page-baseline.json")
SKIP_PAGES = {"template.html", "404.html", "method.html"}
# method.html is generated from MASTER_DATA.md and reproduces every figure in
# it by design, so it agrees or disagrees with everything. The register it is
# built from is checked by check-consistency.py.

FIG = re.compile(r"^[\s]*[-−+]?\$?\s*[0-9][0-9,]*(?:\.[0-9]+)?\s*"
                 r"(?:[KMB]|%|bn|billion|million)?\s*$", re.I)
TOL = 0.015          # 1.5%: rounding, not disagreement
MIN_M = 0.25         # ignore small change; a $200 line is not a headline


class Doc(HTMLParser):
    """Enough of a tree to know a leaf's text and a cell's row and column."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.pairs = []          # (label, raw_value)
        self._skip = 0
        self._tbl = None
        self._row = None
        self._cells = []
        self._leaf = []
        self._leaftag = None

    # -- leaves -------------------------------------------------------
    VOID = {"br", "img", "hr", "input", "meta", "link", "source", "col",
            "area", "base", "embed", "param", "track", "wbr"}

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
            return
        if self._skip or tag in self.VOID:
            return
        if tag == "table":
            self._tbl = {"head": [], "rows": []}
        elif tag == "tr" and self._tbl is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cells.append([])
        # Each open element collects its DIRECT children: ("text", s) for its
        # own text and ("leaf", s) for a child element that held only text.
        # Binding a figure to a sibling under the same parent is the only
        # reliable card rule -- these pages put the label before the value in
        # some cards and after it in others, so neighbour order cannot decide
        # it, and reaching past a neighbour crosses into the next card.
        self.stack.append([tag, []])
        self._leaf = []
        self._leaftag = tag

    def handle_data(self, data):
        if self._skip:
            return
        if self._cells:
            self._cells[-1].append(data)
        if self.stack:
            self.stack[-1][1].append(("text", data))
        self._leaf.append(data)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
            return
        if self._skip or tag in self.VOID:
            return
        if tag in ("td", "th") and self._cells:
            txt = re.sub(r"\s+", " ", "".join(self._cells.pop())).strip()
            if self._row is not None:
                self._row.append(txt)
        elif tag == "tr" and self._row is not None and self._tbl is not None:
            if self._row:
                self._tbl["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._tbl is not None:
            self._emit_table(self._tbl)
            self._tbl = None
        # unwind to the matching open tag
        idx = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                idx = i
                break
        if idx is None:
            return
        node = self.stack.pop(idx)
        del self.stack[idx:]
        kids = node[1]
        own = "".join(s for k, s in kids if k == "text")
        own = re.sub(r"\s+", " ", own).strip()
        if self.stack:
            # a leaf is an element whose content was only its own text
            if own and not any(k == "leaf" for k, _ in kids):
                self.stack[-1][1].append(("leaf", own))
            else:
                self.stack[-1][1].append(("leaf", ""))
        self._emit_card(kids)
        self._leaf = []

    def _emit_card(self, kids):
        leaves = [s for k, s in kids if k == "leaf" and s]
        if not 2 <= len(leaves) <= 6:
            return
        figs = [s for s in leaves if FIG.match(s)]
        labs = [s for s in leaves
                if not FIG.match(s) and len(s) <= 60
                and re.search(r"[A-Za-z]{3}", s)]
        # Exactly one figure and at least one label under one parent: that is a
        # stat card. Anything looser starts guessing.
        if len(figs) == 1 and labs:
            self.pairs.append((labs[0], figs[0]))

    # -- bindings -----------------------------------------------------
    def _emit_table(self, t):
        rows = [r for r in t["rows"] if r]
        if len(rows) < 2:
            return
        head = rows[0]
        # A header row is words; if the first row is figures there is no header
        if sum(1 for c in head[1:] if c and FIG.match(c)) > len(head) / 2:
            return
        for r in rows[1:]:
            if not r or not r[0]:
                continue
            label = r[0]
            for i, cell in enumerate(r[1:], start=1):
                if not cell or not FIG.match(cell):
                    continue
                col = head[i] if i < len(head) else f"col{i}"
                if not col:
                    continue
                self.pairs.append((f"{label} × {col}", cell))


def strip_tags(s):
    s = re.sub(r"<script\b.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style\b.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    return s


def to_millions(tok):
    t = tok.strip().lower().replace("$", "").replace(",", "").replace(" ", "")
    neg = t.startswith(("-", "−"))
    t = t.lstrip("-−+")
    if t.endswith("%"):
        try:
            return ("pct", (-1 if neg else 1) * float(t[:-1]))
        except ValueError:
            return None
    mult = 1 / 1_000_000.0
    for suf, m in (("billion", 1000.0), ("bn", 1000.0), ("million", 1.0),
                   ("b", 1000.0), ("m", 1.0), ("k", 0.001)):
        if t.endswith(suf):
            t, mult = t[: -len(suf)], m
            break
    try:
        return ("num", (-1 if neg else 1) * float(t) * mult)
    except ValueError:
        return None


GEO = {"massachusetts", "new hampshire", "vermont", "maine", "connecticut",
       "rhode island", "new york", "florida", "texas", "california", "boston",
       "us", "usa", "united states", "national"}


def norm_label(s):
    s = htmlmod.unescape(s).lower()
    s = re.sub(r"[^a-z0-9%$.× ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main():
    pages = sorted(f for f in os.listdir(ROOT)
                   if f.endswith(".html") and f not in SKIP_PAGES)
    store = defaultdict(list)
    for page in pages:
        with open(os.path.join(ROOT, page), encoding="utf-8",
                  errors="replace") as fh:
            raw = fh.read()
        src = strip_tags(raw)
        d = Doc()
        try:
            d.feed(src)
        except Exception:
            pass
        for lab, val in d.pairs:
            L = norm_label(lab)
            if len(L) < 8 or L in GEO:
                continue
            if len(L.split()) < 2:
                continue
            v = to_millions(val)
            if not v:
                continue
            kind, n = v
            if kind == "num" and abs(n) < MIN_M:
                continue
            store[(L, kind)].append((page, val, n))

    findings = []
    for (label, kind), rows in store.items():
        pages_seen = {r[0] for r in rows}
        if len(pages_seen) < 2:
            continue
        per = defaultdict(set)
        for p, val, n in rows:
            per[p].add(round(n, 6))
        reps = {p: min(v) for p, v in per.items()}
        lo, hi = min(reps.values()), max(reps.values())
        if lo == hi:
            continue
        base = abs(lo) or 1.0
        if (hi - lo) / base <= TOL:
            continue
        shown = {}
        for p, val, _n in rows:
            shown.setdefault(p, set()).add(val)
        findings.append({
            "label": label, "kind": kind,
            "spread_pct": round((hi - lo) / base * 100, 1),
            "pages": {p: sorted(v) for p, v in sorted(shown.items())},
        })
    findings.sort(key=lambda f: -f["spread_pct"])

    try:
        with open(BASELINE, encoding="utf-8") as fh:
            accepted = set(json.load(fh).get("accepted", []))
    except (OSError, ValueError):
        accepted = set()

    new = [f for f in findings if f["label"] not in accepted]
    print(f"=== cross-page figures: {len(store)} named quantities across "
          f"{len(pages)} pages ===")
    print(f"    {len(findings)} divergent, {len(findings) - len(new)} accepted "
          f"in the baseline\n")
    if "--list" in sys.argv:
        for f in findings:
            mark = " " if f["label"] in accepted else "*"
            print(f"  {mark} [{f['kind']}] {f['label']}   spread {f['spread_pct']}%")
            for p, vals in f["pages"].items():
                print(f"        {p:<36} {', '.join(vals)}")
        print()
    if "--update" in sys.argv:
        with open(BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"note": ("Cross-page differences already examined and "
                                "accepted -- usually one label used for two "
                                "different measures. This list should shrink, "
                                "never grow. Regenerate with --update only "
                                "when removing entries."),
                       "accepted": sorted(f["label"] for f in findings)},
                      fh, indent=1)
            fh.write("\n")
        print(f"baseline rewritten with {len(findings)} accepted labels")
        return 0
    if not new:
        print("No NEW cross-page disagreement.")
        return 0
    print(f"FAIL: {len(new)} NEW cross-page disagreement(s).\n")
    for f in new[:30]:
        print(f"  [{f['kind']}] {f['label']}   spread {f['spread_pct']}%")
        for p, vals in f["pages"].items():
            print(f"      {p:<36} {', '.join(vals)}")
        print()
    print("Either correct the page that is wrong, or -- if one label is being "
          "used for two different measures -- rename one and re-run, or accept "
          "it with --update.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
