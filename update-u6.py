#!/usr/bin/env python3
"""update-u6.py -- refresh MA labor underutilization (U-1..U-6) on the
employment dashboard.

WHY THIS EXISTS
---------------
These figures were a hand-maintained constant. The comment beside them said so
honestly ("the updater does not fetch them"), which is why they sat at Q3 2025
until 2026-09-24 while BLS had published three more quarters: Q4 2025, Q1 2026
and Q2 2026. U-6 had moved 7.2 -> 7.5 and the page still showed 7.2 in the stat
card, the chart, the table and the prose.

Nothing else on the page reads these, so a stale U-6 never tripped a check. It
does now: data/u6-latest.json is in scripts/check-freshness.py.

SOURCE
------
BLS, "Alternative Measures of Labor Underutilization for States" -- quarterly
four-quarter moving averages, not seasonally adjusted.
https://www.bls.gov/lau/stalt.htm

BLS serves that table only as HTML, and both www.bls.gov and download.bls.gov
return 403 to anything automated (verified 2026-09-24). The BLS public API does
not carry the LU database either. FRED redistributes the same table verbatim as
CSV with no key, so that is the transport:

  https://fred.stlouisfed.org/graph/fredgraph.csv?id=U6UNEM6MA

Cross-checked against the seven quarters this page already carried by hand from
BLS: six of seven match to the decimal, and the seventh (Q1 2024 U-6, 6.4 -> 6.2)
moved in BLS's annual revision. So FRED is the BLS series, revised.

THE NATIONAL COLUMN
-------------------
BLS's own table carries a U.S. line computed the same way -- the mean of the
twelve monthly national not-seasonally-adjusted rates over the same span. That
line is not on FRED as a state-basis series, so it is recomputed here from the
national monthly NSA series, which IS its definition. Checked against the
Q3-2025 figures this page carried: U-3, U-4 and U-5 reproduce exactly and U-6
lands 0.1 off on revised data.

October 2025 has no national observation -- the household survey was not
collected that month -- so any window containing it averages eleven months.
That is recorded per row in the data file and noted on the page.
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "employment-dashboard.html")
DATA_FILE = os.path.join(BASE_DIR, "data", "u6-latest.json")

# Neutral skip: the source gave us nothing usable and nothing was written.
# Same convention as update-cbp-encounters.py and update-nyfed-grads.py.
EXIT_BLOCKED = 75

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"

# MA, quarterly 4-quarter moving averages, straight from the BLS table.
MA_SERIES = {f"U-{n}": f"U{n}UNEM{n}MA" for n in range(1, 7)}
# National, monthly, NOT seasonally adjusted -- the inputs to the U.S. line.
NAT_SERIES = {"U-1": "U1RATENSA", "U-2": "U2RATENSA", "U-3": "UNRATENSA",
              "U-4": "U4RATENSA", "U-5": "U5RATENSA", "U-6": "U6RATENSA"}
# MA civilian labour force, monthly, not seasonally adjusted -- the denominator
# the headcount in the prose is measured against. NSA to match the rates.
MA_LF_SERIES = "MALFN"

QUARTERS_ON_CHART = 8      # two years
QUARTERS_IN_TABLE = 3
TABLE_ROWS = ["U-3", "U-4", "U-5", "U-6"]


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def blocked(msg):
    print(f"SKIPPED: {msg}", file=sys.stderr)
    sys.exit(EXIT_BLOCKED)


def half_up(x, places=1):
    """BLS rounds half away from zero; Python's round() goes to even."""
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(1).scaleb(-places)
    return float(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))


def fetch_series(series_id):
    """{'YYYY-MM-DD': float} from FRED's keyless CSV endpoint, via curl.

    Returns None when the fetch fails, so the caller can decide between a hard
    failure and a neutral skip. Missing observations (FRED writes '.') are left
    out rather than read as zero -- October 2025 is a real hole, not a 0.0%
    unemployment rate.
    """
    fd, out = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        r = subprocess.run(
            ["curl", "-sS", "--max-time", "60", "--retry", "3",
             "--retry-delay", "2", "-o", out, "-w", "%{http_code}",
             FRED.format(series_id)],
            capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or r.stdout.strip() != "200":
            return None
        rows = {}
        with open(out, encoding="utf-8-sig") as fh:
            header = fh.readline()
            if "observation_date" not in header:
                return None
            for line in fh:
                parts = line.strip().split(",")
                if len(parts) != 2:
                    continue
                d, v = parts
                if v not in (".", ""):
                    rows[d] = float(v)
        return rows or None
    except (subprocess.SubprocessError, OSError):
        return None
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


def window_months(q_start):
    """The twelve month-keys the 4-quarter average ending at this quarter covers.

    FRED dates each observation at the first month of the FINAL quarter in the
    span, so 2026-04-01 is the average over 2025-07 .. 2026-06.
    """
    y, m, _ = (int(p) for p in q_start.split("-"))
    last = m + 2
    keys = []
    for i in range(12):
        mm, yy = last - i, y
        while mm < 1:
            mm += 12
            yy -= 1
        keys.append(f"{yy}-{mm:02d}-01")
    return list(reversed(keys))


def qlabel(q_start, short=False):
    y, m, _ = (int(p) for p in q_start.split("-"))
    q = (m - 1) // 3 + 1
    return f"Q{q} {y % 100:02d}" if short else f"Q{q} {y}"


def sub(html, pattern, value, what, count=1):
    import re
    new, n = re.subn(pattern, lambda mm: mm.group(1) + value + mm.group(2),
                     html, count=count)
    if n == 0:
        print(f"  WARNING: no marker for {what} -- left as it was")
    return new


def marker(html, tag, value, what):
    import re
    pat = r"(/\*@" + re.escape(tag) + r"\*/).*?(/\*@\*/)"
    new, n = re.subn(pat, lambda mm: mm.group(1) + value + mm.group(2),
                     html, count=1, flags=re.S)
    if n == 0:
        fail(f"marker /*@{tag}*/ is missing from {os.path.basename(HTML_FILE)} "
             f"({what}). Nothing written.")
    return new


def main():
    print("=== MA labor underutilization (BLS state alternative measures) ===\n")

    ma, missing = {}, []
    for name, sid in MA_SERIES.items():
        rows = fetch_series(sid)
        if rows is None:
            missing.append(sid)
        else:
            ma[name] = rows
    if missing:
        blocked(f"FRED did not serve {', '.join(missing)} -- the page keeps "
                f"the figures it has.")

    nat = {}
    for name, sid in NAT_SERIES.items():
        rows = fetch_series(sid)
        if rows is None:
            blocked(f"FRED did not serve the national series {sid}.")
        nat[name] = rows

    lf = fetch_series(MA_LF_SERIES)
    if lf is None:
        blocked(f"FRED did not serve {MA_LF_SERIES} (MA labour force).")

    # Quarters every MA measure has, so a row can never be half a quarter ahead.
    quarters = sorted(set.intersection(*(set(v) for v in ma.values())))
    if len(quarters) < QUARTERS_ON_CHART:
        fail(f"only {len(quarters)} quarters common to all six measures; "
             f"need {QUARTERS_ON_CHART}. Nothing written.")
    chart_q = quarters[-QUARTERS_ON_CHART:]
    latest = chart_q[-1]
    print(f"  newest published quarter: {qlabel(latest)} "
          f"(4-quarter average ending there)")
    for n in TABLE_ROWS:
        print(f"  {n}: " + ", ".join(f"{qlabel(q, True)} {ma[n][q]}"
                                     for q in chart_q[-QUARTERS_IN_TABLE:]))

    # The national line, recomputed on the state table's own basis.
    nat_now, nat_months = {}, {}
    for n in TABLE_ROWS:
        keys = window_months(latest)
        vals = [nat[n][k] for k in keys if k in nat[n]]
        if len(vals) < 11:
            fail(f"national {n} has only {len(vals)} of 12 months in the "
                 f"window ending {qlabel(latest)}. Nothing written.")
        nat_now[n] = half_up(sum(vals) / len(vals))
        nat_months[n] = len(vals)
        if len(vals) < 12:
            gap = [k for k in keys if k not in nat[n]]
            print(f"  note: national {n} averaged over {len(vals)} months "
                  f"(no observation for {', '.join(gap)})")

    # Labour force on the same 12 months, so the headcount in the prose is
    # measured against the quarter it belongs to rather than against today.
    lf_q = {}
    for q in chart_q:
        vals = [lf[k] for k in window_months(q) if k in lf]
        lf_q[q] = round(sum(vals) / len(vals)) if len(vals) >= 11 else None
    if lf_q[latest] is None:
        fail("MA labour force is missing too many months for the newest "
             "quarter. Nothing written.")

    with open(HTML_FILE, encoding="utf-8") as fh:
        html = original = fh.read()

    j = lambda xs: ",".join(str(x) for x in xs)
    html = marker(html, "u6-lab",
                  j(f"'{qlabel(q, True)}'" for q in chart_q), "chart labels")
    html = marker(html, "u6-u6", j(ma["U-6"][q] for q in chart_q), "U-6 series")
    html = marker(html, "u6-u3", j(ma["U-3"][q] for q in chart_q), "U-3 series")
    # The headcount is derived in the page from gap x labour force, so it can
    # never name a different quarter than the two rates beside it.
    html = marker(html, "u6-lf",
                  j(lf_q[q] if lf_q[q] is not None else "null" for q in chart_q),
                  "labour force")

    table_q = chart_q[-QUARTERS_IN_TABLE:]
    for i, q in enumerate(table_q):
        html = sub(html, r'(data-field="u6t-q' + str(i + 1) + r'">)[^<]*(<)',
                   qlabel(q), f"table heading {i + 1}")
    for n in TABLE_ROWS:
        slug = n.lower().replace("-", "")
        for i, q in enumerate(table_q):
            html = sub(html,
                       r'(data-field="u6t-' + slug + "-" + "abc"[i] + r'">)[^<]*(<)',
                       f"{ma[n][q]}%", f"table {n} col {i + 1}")
        html = sub(html, r'(data-field="u6t-' + slug + r'-nat">)[^<]*(<)',
                   f"{nat_now[n]}%", f"table {n} national")
    html = sub(html, r'(data-field="u6t-natmonths">)[^<]*(<)',
               "eleven" if min(nat_months.values()) < 12 else "twelve",
               "national month count")

    out = {
        "series": {n: {"value": ma[n][latest],
                       "period": f"4-quarter average ending {qlabel(latest)}",
                       "national": nat_now.get(n),
                       "national_months_averaged": nat_months.get(n)}
                   for n in MA_SERIES},
        "quarters": [{"quarter": qlabel(q), "fred_date": q,
                      "u3": ma["U-3"][q], "u6": ma["U-6"][q],
                      "labor_force": lf_q[q]} for q in chart_q],
        "verified": date.today().isoformat(),
        "source": ("BLS Alternative Measures of Labor Underutilization for "
                   "States, quarterly 4-quarter moving averages, NSA"),
        "source_url": "https://www.bls.gov/lau/stalt.htm",
        "retrieved_via": ("FRED keyless CSV (U1UNEM1MA..U6UNEM6MA); BLS serves "
                          "this table as HTML only and 403s automated requests"),
        "national_basis": ("mean of the same twelve monthly national NSA rates "
                           "(U1RATENSA, U2RATENSA, UNRATENSA, U4RATENSA, "
                           "U5RATENSA, U6RATENSA); October 2025 has no "
                           "observation, so windows containing it average 11"),
        "meta": {"currency": {"checked": date.today().isoformat(),
                              "newest_available": qlabel(latest),
                              "cadence": "quarterly, about 3 weeks after the "
                                         "quarter's final month"}},
    }
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    prev = None
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, encoding="utf-8") as fh:
                prev = json.load(fh)
        except (OSError, ValueError):
            prev = None
    # Don't churn the timestamp when nothing underneath it moved.
    strip = lambda d: {k: v for k, v in d.items()
                       if k not in ("verified", "meta")} if d else None
    if prev is not None and strip(prev) == strip(out):
        out["verified"] = prev.get("verified", out["verified"])
        out["meta"]["currency"]["checked"] = \
            prev.get("meta", {}).get("currency", {}).get("checked",
                                                         out["meta"]["currency"]["checked"])

    if html == original:
        print("\n  No changes needed.")
    else:
        with open(HTML_FILE, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"\n  Updated {os.path.basename(HTML_FILE)} -> {qlabel(latest)}")
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    print(f"Data -> {DATA_FILE}")


if __name__ == "__main__":
    main()
