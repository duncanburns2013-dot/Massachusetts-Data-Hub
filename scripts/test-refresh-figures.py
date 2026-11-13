"""Figure-value tests: the "broken" path. Prints and exits 0 on pass, 1 on fail.

Stdlib only, no network. These exist because `broken` was unreachable: run() handed
evaluate() an empty dict, so every relation claim came back "suspect", and a suspect is
only reported when a source moved. A sentence on the site could be false and the gate green.

EVERYTHING here goes through run(), on purpose. A first draft of this file tested
evaluate() and read_figures() directly and still passed with both fixes reverted, which
is the exact failure it is supposed to catch. If you add a case, drive it through run().
"""
import dataclasses
import datetime
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.refresh import runner
from scripts.refresh.probes import Probe
from scripts.refresh.register import load_sources
from scripts.refresh.report import write_receipt

SRCS = load_sources(REPO / "data" / "sources.json")
CLAIMS = runner.load_claims(REPO / "data" / "claims.json")
PAGES = ("affordability-dashboard.html", "healthcare-dashboard.html", "tax-budget-dashboard.html")
AUTO = ("ma_auto_above_national", "ma_auto_expenditure_above_note")
fails = []

spec = importlib.util.spec_from_file_location("cf", REPO / "scripts" / "check-freshness.py")
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)


def check(name, cond, detail=""):
    if not cond:
        fails.append(f"{name}: {detail}")


def copy_root():
    d = Path(tempfile.mkdtemp(prefix="figtest-"))
    (d / "data").mkdir()
    for p in PAGES:
        shutil.copy(REPO / p, d / p)
    for f in ("sources.json", "claims.json"):
        shutil.copy(REPO / "data" / f, d / "data" / f)
    return d


def edit(root, page, old, new):
    p = root / page
    t = p.read_bytes().decode("utf-8")
    assert old in t, f"{page}: {old!r} not present to edit"
    p.write_bytes(t.replace(old, new).encode("utf-8"))


def run_at(root, *, moves=(), sources=None):
    """run() with every probe answered, so the only variable is the page content.

    `moves` is {source_id: new_period}; everything else reports the period it holds.
    """
    moves = dict(moves)
    srcs = list(sources if sources is not None else SRCS)
    real = runner.probe
    runner.probe = lambda s, **k: Probe(moves.get(s.id, s.held_period), True, "stub://probe")
    try:
        return runner.run(srcs, CLAIMS, fetch=lambda u: "", today="2026-11-13", root=root)
    finally:
        runner.probe = real


def verdicts(rec):
    return {v.claim_id: v.status for v in rec.verdicts}


def gate(root, rec, name):
    receipt = root / "data" / f"receipt-{name}.json"
    write_receipt(receipt, rec)
    got = json.loads(receipt.read_text(encoding="utf-8"))
    _, problems = cf.check_refresh_receipt(receipt=receipt, today=datetime.date(2026, 11, 13),
                                           sources=root / "data" / "sources.json")
    return got, problems


# --- 1. the live pages: nothing broken, nothing unresolved, no figure unreadable ---
rec = run_at(REPO)
check("live run has no broken claim",
      not [v for v in rec.verdicts if v.status == "broken"], f"{verdicts(rec)}")
check("live run has nothing unresolved",
      not rec.unresolved, f"{[(u.source_id, u.error) for u in rec.unresolved]}")
figs, bad = runner.read_figures(CLAIMS, REPO)
check("live figures all readable", not bad, f"{bad}")
check("live figures are the three a relation needs",
      set(figs) == {"bea_rpp_state", "ma_auto_expenditure", "us_auto_expenditure"}, f"{set(figs)}")

# --- 2. FINDING 1, through run(): MA drops below national, no source moves at all ---
# With evaluate() handed {} this comes back "suspect", and a suspect with no move is
# filtered out, so rec.verdicts is empty and the gate is green. That is the regression.
root = copy_root()
edit(root, "healthcare-dashboard.html",
     "$1,504 per insured vehicle in MA vs. $1,432 nationally",
     "$1,404 per insured vehicle in MA vs. $1,432 nationally")
rec = run_at(root)
st = verdicts(rec)
check("MA below US: both auto claims broken on a quiet run",
      all(st.get(c) == "broken" for c in AUTO), f"{st}")
check("MA below US: nothing else broke",
      {c for c, s in st.items() if s == "broken"} == set(AUTO), f"{st}")
got, problems = gate(root, rec, "auto")
check("broken claims reach the receipt", sorted(got["broken_claims"]) == sorted(AUTO),
      f"{got['broken_claims']}")
check("a broken claim fails the gate", any("BROKEN CLAIMS" in d for _, d in problems), f"{problems}")
shutil.rmtree(root, ignore_errors=True)

# --- 3. the BEA half of finding 1: RPP below a national 100 ---
root = copy_root()
p = root / "affordability-dashboard.html"
t = p.read_bytes().decode("utf-8")
m = runner._COL.search(t)
blob = json.loads(m.group(2))
blob["rpp"]["MA"]["all"] = 97.5
p.write_bytes((t[:m.start(2)] + json.dumps(blob, separators=(",", ":")) + t[m.end(2):]).encode("utf-8"))
st = verdicts(run_at(root))
check("RPP 97.5: both BEA claims broken",
      st.get("ma_price_level_above_us") == "broken" and st.get("ma_rpp_above_national") == "broken",
      f"{st}")
check("RPP 97.5: auto claims untouched", not any(st.get(c) == "broken" for c in AUTO), f"{st}")
shutil.rmtree(root, ignore_errors=True)

# --- 4. an unreadable figure goes UNRESOLVED, never quietly suspect ---
root = copy_root()
edit(root, "healthcare-dashboard.html", "per insured vehicle in MA vs.", "per vehicle in MA versus")
rec = run_at(root)
check("reworded page: both auto figures unresolved",
      {u.source_id for u in rec.unresolved} == {"ma_auto_expenditure", "us_auto_expenditure"},
      f"{[(u.source_id, u.error) for u in rec.unresolved]}")
got, problems = gate(root, rec, "unreadable")
check("an unreadable figure fails the gate",
      any("UNRESOLVED" in d for _, d in problems), f"{problems}")

# --- 5. FINDING 2, through run(): the NAIC edition moves while its figures are unreadable.
# The claims cannot be judged, so they must still be REPORTED as suspect. That only happens
# if the auto figures are known to belong to naic_auto_insurance_database; with FIGURE_SOURCE
# reverted to a bare set they never enter `moved`, moved_claims is empty, and both are dropped.
naic = [s for s in SRCS if s.id == "naic_auto_insurance_database"]
check("the NAIC source is in the register", len(naic) == 1, "missing naic_auto_insurance_database")
if naic:
    probed = dataclasses.replace(naic[0], human_fetch=False, held_period="2024")
    srcs = [probed] + [s for s in SRCS if s.id != naic[0].id]
    rec = run_at(root, moves={"naic_auto_insurance_database": "2025"}, sources=srcs)
    check("a NAIC move is reported",
          [m.source_id for m in rec.deferred] == ["naic_auto_insurance_database"],
          f"deferred={[m.source_id for m in rec.deferred]}")
    st = verdicts(rec)
    check("a NAIC move surfaces its unjudgeable claims as suspect",
          all(st.get(c) == "suspect" for c in AUTO), f"{st}")
shutil.rmtree(root, ignore_errors=True)

check("auto figures are mapped to the NAIC source",
      runner.FIGURE_SOURCE == {"ma_auto_expenditure": "naic_auto_insurance_database",
                               "us_auto_expenditure": "naic_auto_insurance_database"},
      f"{runner.FIGURE_SOURCE}")

if fails:
    print(f"FAIL: {len(fails)} check(s)", file=sys.stderr)
    for f in fails:
        print(f"  {f}", file=sys.stderr)
    sys.exit(1)
print("PASS test-refresh-figures")
