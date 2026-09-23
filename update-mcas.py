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
import re
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "education-statewide.html")
BOSTON_FILE = os.path.join(BASE_DIR, "all-things-boston.html")
MV_FILE = os.path.join(BASE_DIR, "education-merrimack-valley.html")
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


# ── The rest of the statewide page ───────────────────────────────────────────
# Twelve MCAS charts live on education-statewide.html. Three were wired first
# and the other nine were left carrying 2025 behind headings that said 2025 --
# which is worse than an obviously old page, because the two halves disagreed.
# All twelve are written here.

# The four headline cells, in the order overviewCurrent/mcasTrend label them.
HEADLINE = [("ALL (03-08)", "ELA"), ("ALL (03-08)", "MATH"),
            ("10", "ELA"), ("10", "MATH")]
# overviewAll's own order, which is NOT the same.
EVERY_SUBJECT = [("ALL (03-08)", "ELA"), ("ALL (03-08)", "MATH"), ("ALL (03-08)", "SCI"),
                 ("08", "CIV"), ("10", "ELA"), ("10", "MATH"), ("10", "SCI")]
# mcasDecline's subgroups, in its label order.
DECLINE_GROUPS = [("All Students", "All Students"), ("White", "White"),
                  ("Black", "Black or African American"),
                  ("Hispanic", "Hispanic or Latino"), ("Asian", "Asian"),
                  ("Low Income", "Low Income"),
                  ("Disabilities", "Students with Disabilities")]

# The 26 Gateway Cities, MGL c.23A s.3A. Every name is checked against the API
# before use -- a municipality whose district is named differently would
# silently shrink the aggregate rather than raise anything.
GATEWAY_CITIES = [
    "Attleboro", "Barnstable", "Brockton", "Chelsea", "Chicopee", "Everett",
    "Fall River", "Fitchburg", "Haverhill", "Holyoke", "Lawrence", "Leominster",
    "Lowell", "Lynn", "Malden", "Methuen", "New Bedford", "Peabody",
    "Pittsfield", "Quincy", "Revere", "Salem", "Springfield", "Taunton",
    "Westfield", "Worcester",
]
# The fourteen the gatewayCities chart draws. Sorted by ELA at write time, so
# the labels are written with the bars.
GATEWAY_CHART = ["Holyoke", "Lynn", "Lawrence", "Fall River", "Brockton",
                 "Springfield", "Worcester", "Lowell", "Salem", "Malden",
                 "Westfield", "Leominster", "Attleboro", "Quincy"]
TREND_BASE = "2019"          # the pre-pandemic bar the trend chart anchors on
SPEND_FIRST = "2022"


def _state_series():
    """{(sy, grade, subject): row} for every State / All Students row."""
    rows, err = query("org_type='State' AND stu_grp='All Students'",
                      "sy,test_grade,subject_code,m_plus_e_pct,e_pct,m_pct,"
                      "pm_pct,nm_pct,avg_scaled_score,m_plus_e_cnt,stu_cnt",
                      limit=50000)
    if err:
        return None, err
    return {(r["sy"], r["test_grade"], r["subject_code"]): r for r in rows}, None


def update_statewide_rest(html, sy, prev_sy):
    """Writes the nine remaining charts plus the new year-over-year one."""
    st, err = _state_series()
    if err:
        fail(f"could not reach DESE for the state series: {err}")

    def sme(year, grade, subject):
        r = st.get((year, grade, subject))
        return None if r is None else round(float(r["m_plus_e_pct"]) * 100)

    def need(year, grade, subject):
        v = sme(year, grade, subject)
        if v is None:
            fail(f"{year}: State has no {subject} row for grade {grade!r}. "
                 f"Nothing written.")
        return v

    def arr(tag, vals):
        nonlocal html
        pat = r"(/\*@" + tag + r"\*/)[^/]*(/\*@\*/)"
        new, n = re.subn(pat, lambda m: f"{m.group(1)}{vals}{m.group(2)}", html, count=1)
        if not n:
            fail(f"statewide marker @{tag} not found. Nothing written.")
        html = new

    nums = lambda v: ",".join(str(x) for x in v)

    # overviewCurrent / mcasTrend / overviewAll
    cur4 = [need(sy, g, s_) for g, s_ in HEADLINE]
    arr("mcas-ovcur", nums(cur4))
    arr("mcas-ovcur-lab", f"'{sy}'")
    arr("mcas-trend-a", nums([need(TREND_BASE, g, s_) for g, s_ in HEADLINE]))
    arr("mcas-trend-b", nums([need(prev_sy, g, s_) for g, s_ in HEADLINE]))
    arr("mcas-trend-b-lab", f"'{prev_sy}'")
    arr("mcas-trend-c", nums(cur4))
    arr("mcas-trend-c-lab", f"'{sy}'")
    arr("mcas-ovall", nums([need(sy, g, s_) for g, s_ in EVERY_SUBJECT]))

    # gapsLevels -- statewide ELA 3-8 achievement levels.
    r = st.get((sy, "ALL (03-08)", "ELA"))
    lv = [round(float(r[f]) * 100) for f in ("e_pct", "m_pct", "pm_pct", "nm_pct")]
    if not 98 <= sum(lv) <= 102:
        fail(f"{sy}: state ELA levels sum to {sum(lv)}%. Nothing written.")
    if abs((lv[0] + lv[1]) - cur4[0]) > 1:
        fail(f"{sy}: levels say {lv[0] + lv[1]}% meeting-or-above, headline says "
             f"{cur4[0]}%. Nothing written.")
    arr("mcas-levels", nums(lv))

    # spendProf -- the multi-year line, extended rather than shifted.
    years = sorted({y for (y, g, sub_) in st
                    if g == "ALL (03-08)" and sub_ == "ELA" and y >= SPEND_FIRST})
    arr("mcas-spend-lab", ",".join(f"'{y}'" for y in years))
    arr("mcas-spend-ela", nums([need(y, "ALL (03-08)", "ELA") for y in years]))
    arr("mcas-spend-math", nums([need(y, "ALL (03-08)", "MATH") for y in years]))

    # mcasDecline -- grade 10 scaled-score change by subgroup.
    grp, err = query(
        f"sy in('{sy}','{prev_sy}') AND org_type='State' AND test_grade='10' "
        f"AND subject_code in('ELA','MATH')",
        "sy,stu_grp,subject_code,avg_scaled_score", limit=5000)
    if err:
        fail(f"could not reach DESE for subgroup scores: {err}")
    gm = {(r["sy"], r["stu_grp"], r["subject_code"]): r.get("avg_scaled_score")
          for r in grp}

    def delta(subject):
        out = []
        for label, key in DECLINE_GROUPS:
            a, b = gm.get((sy, key, subject)), gm.get((prev_sy, key, subject))
            if a in (None, "") or b in (None, ""):
                fail(f"{sy}: grade 10 {subject} missing for subgroup {key!r} "
                     f"(chart label {label!r}). Nothing written.")
            out.append(round(float(a) - float(b), 1))
        return out

    arr("mcas-decline-ela", nums(delta("ELA")))
    arr("mcas-decline-math", nums(delta("MATH")))

    # Gateway Cities. Aggregated as a weighted mean over students, not a mean of
    # district percentages -- averaging percentages would let Holyoke and
    # Worcester count the same and quietly flatter the group.
    names = "','".join(GATEWAY_CITIES)
    gw, err = query(
        f"sy='{sy}' AND org_type='Public School District' AND stu_grp='All Students' "
        f"AND test_grade='ALL (03-08)' AND subject_code in('ELA','MATH') "
        f"AND dist_name in('{names}')",
        "dist_name,subject_code,m_plus_e_cnt,stu_cnt,m_plus_e_pct", limit=500)
    if err:
        fail(f"could not reach DESE for Gateway Cities: {err}")
    seen = {r["dist_name"] for r in gw}
    absent = [c for c in GATEWAY_CITIES if c not in seen]
    if absent:
        fail(f"{sy}: no district rows for Gateway {absent}. A renamed district "
             f"would shrink the aggregate silently. Nothing written.")
    gwd = {(r["dist_name"], r["subject_code"]): r for r in gw}

    def gw_agg(subject):
        num = sum(float(gwd[(c, subject)]["m_plus_e_cnt"]) for c in GATEWAY_CITIES)
        den = sum(float(gwd[(c, subject)]["stu_cnt"]) for c in GATEWAY_CITIES)
        return round(num / den * 100, 1)

    # "Rest of state" is the state total minus the Gateway share, from counts.
    def rest_agg(subject):
        srow = st.get((sy, "ALL (03-08)", subject))
        tot_n = float(srow["stu_cnt"]) if "stu_cnt" in srow else None
        if tot_n is None:
            fail("state row carries no student count; cannot net out Gateway.")
        tot_me = float(srow["m_plus_e_pct"]) * tot_n
        gnum = sum(float(gwd[(c, subject)]["m_plus_e_cnt"]) for c in GATEWAY_CITIES)
        gden = sum(float(gwd[(c, subject)]["stu_cnt"]) for c in GATEWAY_CITIES)
        return round((tot_me - gnum) / (tot_n - gden) * 100, 1)

    arr("mcas-gwgap-gw", nums([gw_agg("ELA"), gw_agg("MATH")]))
    arr("mcas-gwgap-rest", nums([rest_agg("ELA"), rest_agg("MATH")]))

    chart = sorted(GATEWAY_CHART,
                   key=lambda c: round(float(gwd[(c, "ELA")]["m_plus_e_pct"]) * 100))
    arr("mcas-gwcity-lab", ",".join(f"'{c}'" for c in chart))
    arr("mcas-gwcity-ela",
        nums([round(float(gwd[(c, "ELA")]["m_plus_e_pct"]) * 100) for c in chart]))
    arr("mcas-gwcity-math",
        nums([round(float(gwd[(c, "MATH")]["m_plus_e_pct"]) * 100) for c in chart]))

    # overviewDist -- how many DISTRICTS fall in each ELA band. The labels carry
    # the counts, so labels and slices are written together; letting them drift
    # apart would put one number in the legend and another in the wedge.
    dist, err = query(
        f"sy='{sy}' AND org_type='Public School District' AND stu_grp='All Students' "
        f"AND test_grade='ALL (03-08)' AND subject_code='ELA'",
        "dist_name,m_plus_e_pct", limit=5000)
    if err:
        fail(f"could not reach DESE for the district distribution: {err}")
    bands = [0, 0, 0, 0]
    for r in dist:
        v = float(r["m_plus_e_pct"]) * 100
        bands[0 if v < 25 else 1 if v < 50 else 2 if v < 75 else 3] += 1
    if sum(bands) != len(dist):
        fail("district distribution lost a district. Nothing written.")
    arr("mcas-ovdist", nums(bands))
    arr("mcas-ovdist-lab",
        f"'<25% Meeting ({bands[0]})','25-50% Meeting ({bands[1]})',"
        f"'50-75% Meeting ({bands[2]})','≥75% Meeting ({bands[3]})'")
    print(f"  district ELA bands ({len(dist)} districts): {bands}")

    # The new year-over-year chart: percentage-point change on every subject.
    yoy = []
    for g, sub_ in EVERY_SUBJECT:
        a, b = sme(sy, g, sub_), sme(prev_sy, g, sub_)
        yoy.append(None if (a is None or b is None) else a - b)
    arr("mcas-yoy", ",".join("null" if v is None else str(v) for v in yoy))

    html = sub(html, r'(data-field="mcas-prev-year">)[^<]*(<)', prev_sy,
               "previous-year label", count=0)
    html = sub(html, r'(data-field="mcas-first-year">)[^<]*(<)', years[0],
               "first-year label", count=0)
    return html


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
# e2 / gapChange label sets. DESE's names differ from the chart's shorthand:
# "EconDis" is Low Income, "Sped" is Students with Disabilities.
BOS_E2_GROUPS = [("All", "All Students"), ("EL", "English Learners"),
                 ("Black", "Black or African American"),
                 ("Hispanic", "Hispanic or Latino"), ("EconDis", "Low Income"),
                 ("Sped", "Students with Disabilities")]
BOS_SPECIAL = [("All Students", "All Students"), ("High Needs", "High Needs"),
               ("Low Income", "Low Income"),
               ("EL/Former EL", "English Learners and Former English Learners"),
               ("Disability", "Students with Disabilities")]
BOS_HS_RACE = [("White", "White"), ("Asian", "Asian"),
               ("Multi-Race", "Multi-Race, Not Hispanic or Latino"),
               ("All", "All Students"), ("Black", "Black or African American"),
               ("Hispanic", "Hispanic or Latino"), ("EL", "English Learners"),
               ("Disability", "Students with Disabilities")]
BOS_CHG = [("All", "All Students"), ("Asian", "Asian"), ("White", "White"),
           ("Multi-Race", "Multi-Race, Not Hispanic or Latino"),
           ("Hispanic", "Hispanic or Latino"),
           ("Black", "Black or African American"), ("EL", "English Learners"),
           ("Disability", "Students with Disabilities")]

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

    prev_rows, err = query(
        f"sy='{int(sy) - 1}' AND stu_grp='All Students' AND ((org_type='State') OR "
        f"(org_type='Public School District' AND dist_name='Boston'))",
        "org_type,test_grade,subject_code,m_plus_e_pct")
    if err:
        return False, err
    prev_by = {}
    for r in prev_rows:
        who = "State" if r["org_type"] == "State" else "Boston"
        prev_by[(who, r["test_grade"], r["subject_code"])] = r

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

    # The six charts that were missed on the first pass, plus the new
    # year-over-year pair. All of them are subgroup work, and DESE's subgroup
    # names are not the chart's shorthand: "EconDis" is Low Income and "Sped" is
    # Students with Disabilities, so every mapping is spelled out above rather
    # than guessed from the label.
    prev_sy = str(int(sy) - 1)
    sg, err = query(
        f"sy in('{sy}','{prev_sy}') AND org_type='Public School District' "
        f"AND dist_name='Boston' AND test_grade in('ALL (03-08)','10') "
        f"AND subject_code in('ELA','MATH')",
        "sy,stu_grp,test_grade,subject_code,avg_scaled_score", limit=5000)
    if err:
        return False, err
    sgm = {(r["sy"], r["stu_grp"], r["test_grade"], r["subject_code"]):
           r.get("avg_scaled_score") for r in sg}

    def score(year, grp, grade, subject, label):
        v = sgm.get((year, grp, grade, subject))
        if v in (None, ""):
            fail(f"{year}: Boston has no {subject} grade-{grade} score for "
                 f"{grp!r} (chart label {label!r}). Nothing written.")
        return float(v)

    arr("bos-e6", ssela)
    arr("bos-gapsp-ela",
        [score(sy, k, "ALL (03-08)", "ELA", l) for l, k in BOS_SPECIAL])
    arr("bos-gapsp-math",
        [score(sy, k, "ALL (03-08)", "MATH", l) for l, k in BOS_SPECIAL])
    arr("bos-gaphs", [score(sy, k, "10", "ELA", l) for l, k in BOS_HS_RACE])
    arr("bos-e2", [round(score(sy, k, "10", "ELA", l)
                         - score(prev_sy, k, "10", "ELA", l), 1)
                   for l, k in BOS_E2_GROUPS])
    arr("bos-gapchg", [round(score(sy, k, "10", "ELA", l)
                             - score(prev_sy, k, "10", "ELA", l), 1)
                       for l, k in BOS_CHG])
    html = sub(html, r"(/\*@bos-chg-years\*/)[^/]*(/\*@\*/)",
               f"'{prev_sy}-{sy}'", "Boston change-years label")

    # Year-over-year, Boston against the state on the same six cells.
    def yoy(who):
        out = []
        for g, sub_ in BOS_OVBAR:
            a, b = by.get((who, g, sub_)), prev_by.get((who, g, sub_))
            if a is None or b is None:
                out.append("null")
            else:
                out.append(round(float(a["m_plus_e_pct"]) * 100
                                 - float(b["m_plus_e_pct"]) * 100))
        return out

    arr("bos-yoy-b", yoy("Boston"))
    arr("bos-yoy-s", yoy("State"))
    html = sub(html, r'(data-field="bos-prev-year">)[^<]*(<)', prev_sy,
               "Boston previous-year label", count=0)
    html = sub(html, r'(data-field="bos-mcas-year">)[^<]*(<)', sy,
                   "Boston year label", count=0)

    if html != orig:
        with open(BOSTON_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        return True, (f"Boston updated -- ELA 3-8 {ovbar_b[0]}% vs state "
                      f"{ovbar_s[0]}%, grade 10 ELA {ovbar_b[2]}% vs {ovbar_s[2]}%")
    return True, "Boston already current"


# ── Merrimack Valley (education-merrimack-valley.html) ───────────────────────
# This page drives roughly fifteen charts off a single `const D = {...}` JSON
# literal, so it is edited as JSON rather than through markers: parse, replace
# only the MCAS-derived keys, re-serialise. Everything else in D -- growth,
# accountability points, absenteeism, graduation, money -- comes from other DESE
# releases this script does not fetch and is left exactly as found.
MV_DISTRICTS = {"haverhill": "Haverhill", "methuen": "Methuen",
                "lawrence": "Lawrence", "state": None}   # None = the State rows

# D.subjLabels order.
MV_SUBJ = [("ALL (03-08)", "ELA"), ("ALL (03-08)", "MATH"), ("ALL (03-08)", "SCI"),
           ("08", "CIV"), ("10", "ELA"), ("10", "MATH"), ("10", "SCI")]
MV_GRADES = ["03", "04", "05", "06", "07", "08", "10"]

# D.groupLabels -> the subgroup name DESE publishes.
MV_GROUPS = [
    ("All", "All Students"),
    ("High Needs", "High Needs"),
    ("Low Income", "Low Income"),
    ("EL/Former EL", "English Learners and Former English Learners"),
    ("Disability", "Students with Disabilities"),
    ("Asian", "Asian"),
    ("Black", "Black or African American"),
    ("Hispanic", "Hispanic or Latino"),
    ("Multi-Race", "Multi-Race, Not Hispanic or Latino"),
    ("White", "White"),
]


def _mv_fetch(sy):
    """{(district_key, stu_grp, test_grade, subject): row} for one school year."""
    names = "','".join(v for v in MV_DISTRICTS.values() if v)
    rows, err = query(
        f"sy='{sy}' AND ((org_type='State') OR (org_type='Public School District' "
        f"AND dist_name in('{names}')))",
        "org_type,dist_name,stu_grp,test_grade,subject_code,m_plus_e_pct,"
        "e_pct,m_pct,pm_pct,nm_pct,avg_scaled_score,stu_cnt", limit=50000)
    if err:
        return None, err
    out = {}
    rev = {v: k for k, v in MV_DISTRICTS.items() if v}
    for r in rows:
        key = "state" if r["org_type"] == "State" else rev.get(r["dist_name"])
        if key:
            out[(key, r["stu_grp"], r["test_grade"], r["subject_code"])] = r
    return out, None


def update_merrimack(sy):
    cur, err = _mv_fetch(sy)
    if err:
        return False, err
    prev, err = _mv_fetch(str(int(sy) - 1))
    if err:
        return False, err

    with open(MV_FILE, encoding="utf-8") as f:
        html = orig = f.read()
    m = re.search(r"(const D = )(\{.*?\})(;\s*\n)", html, re.S)
    if not m:
        fail("the D object on the Merrimack page was not found. Nothing written.")
    D = json.loads(m.group(2))

    def row(store, k, grade, subject, grp="All Students"):
        return store.get((k, grp, grade, subject))

    def me(store, k, grade, subject, grp="All Students"):
        r = row(store, k, grade, subject, grp)
        return None if r is None else round(float(r["m_plus_e_pct"]) * 100)

    def ss(store, k, grade, subject, grp="All Students"):
        r = row(store, k, grade, subject, grp)
        v = None if r is None else r.get("avg_scaled_score")
        return None if v in (None, "") else float(v)

    # 1. subj -- the seven headline cells per entity.
    for k in MV_DISTRICTS:
        vals = [me(cur, k, g, sub_) for g, sub_ in MV_SUBJ]
        if vals[0] is None:
            fail(f"{sy}: no ELA 3-8 row for {k}. Nothing written.")
        D["subj"][k] = [v if v is not None else None for v in vals]

    # 2. grades -- percentage and scaled score, by grade.
    for k in MV_DISTRICTS:
        D["grades"][k]["ela_me"] = [me(cur, k, g, "ELA") for g in MV_GRADES]
        D["grades"][k]["math_me"] = [me(cur, k, g, "MATH") for g in MV_GRADES]
        D["grades"][k]["ela_ss"] = [ss(cur, k, g, "ELA") for g in MV_GRADES]
        D["grades"][k]["math_ss"] = [ss(cur, k, g, "MATH") for g in MV_GRADES]

    # 3. gaps -- scaled score by subgroup. A suppressed subgroup is null, not a
    #    failure: DESE withholds small cells routinely and the chart already
    #    draws gaps for them. Only the All Students row must exist.
    for k in D["gaps"]:
        for field, grade, subject in (("ela_nhs", "ALL (03-08)", "ELA"),
                                      ("math_nhs", "ALL (03-08)", "MATH"),
                                      ("sci_nhs", "ALL (03-08)", "SCI"),
                                      ("ela_hs", "10", "ELA"),
                                      ("math_hs", "10", "MATH"),
                                      ("sci_hs", "10", "SCI")):
            now = [ss(cur, k, grade, subject, g) for _, g in MV_GROUPS]
            if now[0] is None:
                fail(f"{sy}: no All Students {subject} {grade} row for {k}. "
                     f"Nothing written.")
            D["gaps"][k][field] = now
            chg = field + "_chg"
            if chg in D["gaps"][k]:
                was = [ss(prev, k, grade, subject, g) for _, g in MV_GROUPS]
                D["gaps"][k][chg] = [
                    None if (a is None or b is None) else round(a - b, 1)
                    for a, b in zip(now, was)]

    # 4. levels -- the E/M/PM/NM split of ELA 3-8. Checked against subj, because
    #    a level split whose meeting-or-above half disagrees with the headline
    #    percentage is the clearest sign the wrong row was read.
    for k in D["levels"]:
        r = row(cur, k, "ALL (03-08)", "ELA")
        if r is None:
            fail(f"{sy}: no ELA 3-8 levels for {k}. Nothing written.")
        lv = [round(float(r[f]) * 100) for f in ("e_pct", "m_pct", "pm_pct", "nm_pct")]
        if not 98 <= sum(lv) <= 102:
            fail(f"{sy}: {k} ELA levels sum to {sum(lv)}%, not ~100. Nothing written.")
        if abs((lv[0] + lv[1]) - D["subj"][k][0]) > 1:
            fail(f"{sy}: {k} levels say {lv[0] + lv[1]}% meeting-or-above but the "
                 f"headline says {D['subj'][k][0]}%. Nothing written.")
        D["levels"][k] = lv

    # 5. yoy -- percentage-point change on the same seven cells, for the new
    #    year-over-year chart. Computed here so it can never disagree with the
    #    subj bars it sits beside.
    D["yoy"] = {}
    for k in MV_DISTRICTS:
        row_ = []
        for g, sub_ in MV_SUBJ:
            a, b = me(cur, k, g, sub_), me(prev, k, g, sub_)
            row_.append(None if (a is None or b is None) else a - b)
        D["yoy"][k] = row_

    # 6. tested counts.
    for k in D.get("tested", {}):
        r = row(cur, k, "ALL (03-08)", "ELA")
        if r:
            D["tested"][k] = float(r["stu_cnt"])
    for k in D.get("tested10", {}):
        r = row(cur, k, "10", "ELA")
        if r:
            D["tested10"][k] = float(r["stu_cnt"])

    html = html[:m.start(2)] + json.dumps(D, separators=(",", ":")) + html[m.end(2):]
    html = sub(html, r'(data-field="mv-mcas-year">)[^<]*(<)', sy,
               "Merrimack year label", count=0)
    html = sub(html, r'(data-field="mv-prev-year">)[^<]*(<)', str(int(sy) - 1),
               "Merrimack previous-year label", count=0)

    if html != orig:
        with open(MV_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        return True, ("Merrimack updated -- ELA 3-8 Haverhill "
                      f"{D['subj']['haverhill'][0]}%, Methuen "
                      f"{D['subj']['methuen'][0]}%, Lawrence "
                      f"{D['subj']['lawrence'][0]}%, state {D['subj']['state'][0]}%")
    return True, "Merrimack already current"


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
    html = update_statewide_rest(html, sy, str(int(sy) - 1))

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

    ok, msg = update_merrimack(sy)
    if ok:
        print(f"  {msg}")
    else:
        print(f"  !! Merrimack NOT updated: {msg}", file=sys.stderr)

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Data -> {DATA_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
