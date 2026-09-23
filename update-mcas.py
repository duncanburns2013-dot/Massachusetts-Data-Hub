#!/usr/bin/env python3
"""update-mcas.py — refresh MCAS achievement figures from DESE.

WHY THIS EXISTS
---------------
The education dashboards carried 2025 MCAS by hand. DESE published 2026 on
2026-09-22 and nothing moved, because nothing was wired: these pages had no
updater at all and the freshness watchdog could only ever tell you they were old.

SOURCE
------
DESE's own full dataset, the one the "Get Full Dataset" button on
profiles.doe.mass.edu/statereport/mcas.aspx points at. It is a Socrata table, so
it has a JSON API and needs no key:

  https://educationtocareer.data.mass.gov/resource/i9w6-niyt.json

Verified against the rendered state report on 2026-09-23: the API's SY2026
State / All Students rows reproduce the on-page grid exactly, and reproduce the
three .xlsx exports DESE hands out from that page.

A NOTE ON GRADE SPANS
---------------------
`test_grade` carries individual grades ('03'..'08', '10'), the rollup
'ALL (03-08)', and 'HS SCI' for the high-school science tests. These are NOT
interchangeable and the .xlsx exports do not say which span they are: the three
files DESE gives you are distinguishable only by their totals. Read the span
from this column, never infer it from a row count.

  ALL (03-08) SCI is grades 5 and 8 only -- the two grades that sit the test --
  which is why the page labels that bar "Science 5 & 8" and why its tested
  count is about a third of the ELA one.

No API key needed.
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "education-statewide.html")
DATA_FILE = os.path.join(BASE_DIR, "data", "mcas-latest.json")
API = "https://educationtocareer.data.mass.gov/resource/i9w6-niyt.json"

# Exit code for "the source gave us nothing usable, nothing written" -- a
# neutral skip, same convention as update-cbp-encounters.py.
EXIT_BLOCKED = 75

# The statewide page's three MCAS bars, in the order their labels appear.
ELA_GRADES = ["03", "04", "05", "06", "07", "08", "10"]
MATH_GRADES = ELA_GRADES
# ('Science 5 & 8', 'Civics Gr.8', 'Science Gr.10')
SCI_CELLS = [("ALL (03-08)", "SCI"), ("08", "CIV"), ("10", "SCI")]


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def query(where, select, limit=2000):
    """Socrata query via curl -- mass.gov hosts sit behind a bot filter."""
    qs = urllib.parse.urlencode({"$select": select, "$where": where,
                                 "$limit": str(limit)})
    fd, out = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        p = subprocess.run(["curl", "-sS", "--max-time", "120", "-o", out,
                            "-w", "%{http_code}", f"{API}?{qs}"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            return None, f"curl exit {p.returncode}: {p.stderr.strip()[:160]}"
        if p.stdout.strip() != "200":
            return None, f"HTTP {p.stdout.strip()}"
        with open(out, encoding="utf-8") as f:
            return json.load(f), None
    except ValueError as e:
        return None, f"bad JSON: {e}"
    finally:
        try:
            os.remove(out)
        except OSError:
            pass


def pct(row):
    """Socrata stores the percentage as a fraction. 0.43 -> 43."""
    return round(float(row["m_plus_e_pct"]) * 100)


def sub(html, pattern, value, what):
    import re
    new, n = re.subn(pattern, lambda m: f"{m.group(1)}{value}{m.group(2)}",
                     html, count=1)
    if not n:
        fail(f"anchor for {what} not found -- page structure changed. "
             f"Nothing written.")
    return new


def main():
    print("=== MCAS achievement (DESE) ===\n")

    # Newest school year present, rather than this calendar year: the release
    # lands in September and the column is a school year, so guessing from the
    # clock is wrong for a third of the year either side of it.
    rows, err = query("org_type='State'", "sy", limit=50000)
    if err:
        print(f"  !! could not reach DESE: {err}", file=sys.stderr)
        return EXIT_BLOCKED
    sy = max(r["sy"] for r in rows)
    print(f"  newest school year published: {sy}")

    rows, err = query(
        f"sy='{sy}' AND org_type='State' AND stu_grp='All Students'",
        "test_grade,subject_code,m_plus_e_pct,avg_scaled_score,stu_cnt")
    if err:
        print(f"  !! could not reach DESE: {err}", file=sys.stderr)
        return EXIT_BLOCKED

    by = {(r["test_grade"], r["subject_code"]): r for r in rows}

    def cell(grade, subject):
        r = by.get((grade, subject))
        if r is None:
            fail(f"{sy} State has no {subject} row for grade {grade!r}. "
                 f"DESE changed the table; nothing written.")
        return r

    ela = [pct(cell(g, "ELA")) for g in ELA_GRADES]
    math = [pct(cell(g, "MATH")) for g in MATH_GRADES]
    sci = [pct(cell(g, s)) for g, s in SCI_CELLS]

    print(f"  ELA  by grade {ELA_GRADES}: {ela}")
    print(f"  MATH by grade {MATH_GRADES}: {math}")
    print(f"  SCI/CIV {[f'{g} {s}' for g, s in SCI_CELLS]}: {sci}")

    with open(HTML_FILE, encoding="utf-8") as f:
        html = orig = f.read()

    html = sub(html, r"(data:\[/\*@mcas-ela\*/)[^\]]*(/\*@\*/\])",
               ",".join(map(str, ela)), "ELA bars")
    html = sub(html, r"(data:\[/\*@mcas-math\*/)[^\]]*(/\*@\*/\])",
               ",".join(map(str, math)), "Math bars")
    html = sub(html, r"(data:\[/\*@mcas-sci\*/)[^\]]*(/\*@\*/\])",
               ",".join(map(str, sci)), "Science/Civics bars")
    html = sub(html, r'(data-field="mcas-year">)[^<]*(<)', sy, "year label")

    if html != orig:
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n  -> {os.path.basename(HTML_FILE)} written.")
    else:
        print("\n  No changes needed.")

    # A data file so scripts/check-freshness.py can age this feed by its own
    # published school year rather than by whenever someone last edited a page.
    out = {
        "school_year": sy,
        "checked": date.today().isoformat(),
        "source": "MA DESE via educationtocareer.data.mass.gov resource i9w6-niyt",
        "url": f"{API}?$where=sy='{sy}' AND org_type='State'",
        "note": ("ALL (03-08) SCI covers grades 5 and 8 only. test_grade is "
                 "authoritative for the span; do not infer it from row counts."),
        "state_all_students": {
            f"{g}_{s}": {"m_plus_e_pct": pct(cell(g, s)),
                         "avg_scaled_score": cell(g, s).get("avg_scaled_score"),
                         "students": int(cell(g, s)["stu_cnt"])}
            for g, s in ([(g, "ELA") for g in ELA_GRADES]
                         + [(g, "MATH") for g in MATH_GRADES] + SCI_CELLS)
        },
    }
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Data -> {DATA_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
