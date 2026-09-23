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
BOSTON_FILE = os.path.join(BASE_DIR, "all-things-boston.html")
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


def sub(html, pattern, value, what, count=1):
    """count=0 replaces EVERY occurrence. The year label appears more than once
    on a page (heading and source line); writing only the first leaves the other
    asserting last year's release next to this year's bars, which is the drift
    this whole script exists to end."""
    import re
    new, n = re.subn(pattern, lambda m: f"{m.group(1)}{value}{m.group(2)}",
                     html, count=count)
    if not n:
        fail(f"anchor for {what} not found -- page structure changed. "
             f"Nothing written.")
    return new


# ── Boston (all-things-boston.html) ──────────────────────────────────────────
# Nine charts, every one of them Boston against the State on the same cells, so
# both columns are written from the same pull. The orders below are the chart's
# OWN label order and they differ between charts -- overviewBar runs
# ELA/Math/ELA10/Math10/Sci/Sci10 while overviewAll puts science third. Getting
# these out of step would leave each bar carrying the wrong subject's number
# with nothing on screen to show it, so each order sits next to its tag.
BOS_GRADES = ["03", "04", "05", "06", "07", "08", "10"]
BOS_OVBAR = [("ALL (03-08)", "ELA"), ("ALL (03-08)", "MATH"), ("10", "ELA"),
             ("10", "MATH"), ("ALL (03-08)", "SCI"), ("10", "SCI")]
BOS_OVALL = [("ALL (03-08)", "ELA"), ("ALL (03-08)", "MATH"), ("ALL (03-08)", "SCI"),
             ("10", "ELA"), ("10", "MATH"), ("10", "SCI"), ("08", "CIV")]
BOS_SCI = [("05", "SCI"), ("08", "SCI"), ("08", "CIV"), ("10", "SCI")]
# Chart label -> the subgroup name DESE actually publishes. "EL" is "English
# Learners", plural; the singular returns nothing and would silently drop a bar.
BOS_GAP_GROUPS = [
    ("White", "White"), ("Asian", "Asian"),
    ("Multi-Race", "Multi-Race, Not Hispanic or Latino"),
    ("All Students", "All Students"),
    ("Black", "Black or African American"),
    ("Hispanic", "Hispanic or Latino"),
    ("EL", "English Learners"),
    ("Disability", "Students with Disabilities"),
]


def update_boston(sy):
    """Returns (ok, message). A missing cell is fatal -- a half-written chart is
    worse than yesterday's, because it looks finished."""
    rows, err = query(
        f"sy='{sy}' AND stu_grp='All Students' AND ((org_type='State') OR "
        f"(org_type='Public School District' AND dist_name='Boston'))",
        "org_type,test_grade,subject_code,m_plus_e_pct,e_pct,m_pct,pm_pct,"
        "nm_pct,avg_scaled_score")
    if err:
        return False, err
    by = {}
    for r in rows:
        who = "State" if r["org_type"] == "State" else "Boston"
        by[(who, r["test_grade"], r["subject_code"])] = r

    def cell(who, g, sub_):
        r = by.get((who, g, sub_))
        if r is None:
            fail(f"{sy}: no {sub_} row for {who} grade {g!r}. Nothing written.")
        return r

    pc = lambda w, g, s: round(float(cell(w, g, s)["m_plus_e_pct"]) * 100)
    sc = lambda w, g, s: int(cell(w, g, s)["avg_scaled_score"])

    ovbar_b = [pc("Boston", *c) for c in BOS_OVBAR]
    ovbar_s = [pc("State", *c) for c in BOS_OVBAR]
    ovall_b = [pc("Boston", *c) for c in BOS_OVALL]
    ovall_s = [pc("State", *c) for c in BOS_OVALL]
    ovall_g = [b - st for b, st in zip(ovall_b, ovall_s)]
    gela_b = [pc("Boston", g, "ELA") for g in BOS_GRADES]
    gela_s = [pc("State", g, "ELA") for g in BOS_GRADES]
    gmath_b = [pc("Boston", g, "MATH") for g in BOS_GRADES]
    gmath_s = [pc("State", g, "MATH") for g in BOS_GRADES]
    ssela = [sc("Boston", g, "ELA") for g in BOS_GRADES]
    ssmath = [sc("Boston", g, "MATH") for g in BOS_GRADES]
    gsci_b = [pc("Boston", *c) for c in BOS_SCI]
    gsci_s = [pc("State", *c) for c in BOS_SCI]

    lv = cell("Boston", "ALL (03-08)", "ELA")
    pie = [round(float(lv[k]) * 100) for k in ("e_pct", "m_pct", "pm_pct", "nm_pct")]
    if not 98 <= sum(pie) <= 102:
        fail(f"Boston ELA levels sum to {sum(pie)}%, not ~100. Nothing written.")

    # Subgroup scaled scores, one query so a renamed group is obvious.
    grp, err = query(
        f"sy='{sy}' AND org_type='Public School District' AND dist_name='Boston' "
        f"AND test_grade='ALL (03-08)' AND subject_code in('ELA','MATH')",
        "stu_grp,subject_code,avg_scaled_score")
    if err:
        return False, err
    gmap = {(r["stu_grp"], r["subject_code"]): r.get("avg_scaled_score") for r in grp}

    def gaps(subject):
        out = []
        for label, key in BOS_GAP_GROUPS:
            v = gmap.get((key, subject))
            if v is None:
                fail(f"{sy}: Boston has no {subject} row for subgroup {key!r} "
                     f"(chart label {label!r}). Nothing written.")
            out.append(float(v))
        return out

    gapela, gapmath = gaps("ELA"), gaps("MATH")

    with open(BOSTON_FILE, encoding="utf-8") as f:
        html = orig = f.read()

    def arr(tag, vals):
        nonlocal html
        import re
        pat = r"(\[/\*@" + tag + r"\*/)[^\]]*(/\*@\*/\])"
        new, n = re.subn(pat, lambda m: f"{m.group(1)}{','.join(map(str, vals))}{m.group(2)}",
                         html, count=1)
        if not n:
            fail(f"Boston marker @{tag} not found. Nothing written.")
        html = new

    arr("bos-ovbar-b", ovbar_b);  arr("bos-ovbar-s", ovbar_s)
    arr("bos-ovpie", pie)
    arr("bos-ovall-b", ovall_b);  arr("bos-ovall-s", ovall_s);  arr("bos-ovall-g", ovall_g)
    arr("bos-gela-b", gela_b);    arr("bos-gela-s", gela_s)
    arr("bos-gmath-b", gmath_b);  arr("bos-gmath-s", gmath_s)
    arr("bos-ssela", ssela);      arr("bos-ssmath", ssmath)
    arr("bos-gsci-b", gsci_b);    arr("bos-gsci-s", gsci_s)
    arr("bos-gapela", gapela);    arr("bos-gapmath", gapmath)
    html = sub(html, r'(data-field="bos-mcas-year">)[^<]*(<)', sy,
                   "Boston year label", count=0)

    if html != orig:
        with open(BOSTON_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        return True, (f"Boston updated -- ELA 3-8 {ovbar_b[0]}% vs state "
                      f"{ovbar_s[0]}%, grade 10 ELA {ovbar_b[2]}% vs {ovbar_s[2]}%")
    return True, "Boston already current"


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
    html = sub(html, r'(data-field="mcas-year">)[^<]*(<)', sy, "year label", count=0)

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
    ok, msg = update_boston(sy)
    if ok:
        print(f"  {msg}")
    else:
        print(f"  !! Boston NOT updated: {msg}", file=sys.stderr)

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Data -> {DATA_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
