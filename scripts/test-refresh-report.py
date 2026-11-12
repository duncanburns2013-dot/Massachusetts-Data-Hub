"""Report, receipt and gate tests. Prints and exits 0 on pass, 1 on fail. Stdlib only, no network."""
import dataclasses
import datetime
import importlib.util
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.refresh import runner
from scripts.refresh.claims import Claim, UnknownFigure, Verdict, load_claims
from scripts.refresh.probes import NotFound
from scripts.refresh.register import load_sources
from scripts.refresh.report import RunRecord, format_message, write_receipt
from scripts.refresh.runner import Applied, Failure, Move, Skipped

spec = importlib.util.spec_from_file_location("check_freshness", REPO / "scripts" / "check-freshness.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

TODAY = datetime.date(2026, 11, 12)
tmp = Path(tempfile.mkdtemp())

try:
    acs_applied = Applied(
        "census_acs1_ma_income",
        {"household": 99000.0, "family": 120000.0, "vintage": 2024, "source": "old"},
        {"household": 106539.0, "family": 138434.0, "vintage": 2025, "source": "new"},
        ["affordability-dashboard.html"], [])
    broken = Verdict("ma_auto_above_national", "broken")

    # 1. silence: nothing moved, nothing broke -> no message at all
    assert format_message(RunRecord(applied=[], verdicts=[])) is None
    assert format_message(RunRecord(verdicts=[Verdict("a", "holds")])) is None
    # ... and a message the moment anything is worth saying
    msg = format_message(RunRecord(applied=[acs_applied], verdicts=[broken]))
    assert "106,539" in msg and "broken" in msg.lower() and "ma_auto_above_national" in msg, msg
    for r in (RunRecord(verdicts=[Verdict("s", "suspect")]),
              RunRecord(unresolved=[Failure("x", "boom")]),
              RunRecord(deferred=[Move("bea_rpp_state", "2024", "2025", True, "u")]),
              RunRecord(overdue=[Skipped("doi", "2026-01-01", "2027")]),
              RunRecord(applied=[Applied("s", {"household": 99000.0, "family": 120000.0, "vintage": 2024, "source": "old"}, {"household": 106539.0, "family": 138434.0, "vintage": 2025, "source": "new"}, ["a.html"], ["b.json"])])):
        assert format_message(r) is not None, r
    # the message names the page and sentence, not just the id; long text is truncated
    cl = [Claim(id="c1", page="p.html", text="MA auto costs more " + "x" * 300, figures=[])]
    m = format_message(RunRecord(verdicts=[Verdict("c1", "broken"), Verdict("c2", "suspect")], claims=cl))
    assert "p.html: MA auto costs more" in m and "[c1]" in m and "c1: broken" not in m and "..." in m, m
    assert "x" * 200 not in m and "c2" in m  # unknown id falls back to the id
    # a source with no due date is reported as such, not silently fine
    assert "no due date" in format_message(RunRecord(overdue=[Skipped("doi", None, "2027")]))
    # a leaked key is scrubbed from the message
    os.environ["CENSUS_API_KEY"] = "sekrit123"
    assert "sekrit123" not in format_message(RunRecord(unresolved=[Failure("x", "url?key=sekrit123")]))

    # 2. receipt: exact shape; ids and dates only
    p = tmp / "receipt.json"
    write_receipt(p, RunRecord(
        applied=[acs_applied], verdicts=[broken, Verdict("s", "suspect"), Verdict("h", "holds")],
        unresolved=[Failure("census_acs1_ma_income", "boom")],
        deferred=[Move("bea_rpp_state", "2024", "2025", True, "u")],
        overdue=[Skipped("doi_merged_market_rates", "2026-01-01", "2027")],
        run_date="2026-11-12"))
    got = json.loads(p.read_text(encoding="utf-8"))
    assert got == {"last_run": "2026-11-12", "unresolved": ["census_acs1_ma_income"],
                   "broken_claims": ["ma_auto_above_national"], "deferred": ["bea_rpp_state"],
                   "overdue_human_fetch": ["doi_merged_market_rates"], "divergent": []}, got
    # a target that still disagrees after the write reaches the receipt, so the gate can see it
    diverged = Applied("census_acs1_ma_income", {"household": 99000.0, "family": 120000.0, "vintage": 2024, "source": "old"}, {"household": 106539.0, "family": 138434.0, "vintage": 2025, "source": "new"}, ["affordability-dashboard.html"],
                       ["data/burden-constants.json"])
    write_receipt(p, RunRecord(applied=[diverged], run_date="2026-11-12"))
    assert json.loads(p.read_text(encoding="utf-8"))["divergent"] == ["census_acs1_ma_income"]
    assert not (tmp / "receipt.json.tmp").exists()
    write_receipt(p, RunRecord())  # default run_date is today
    assert json.loads(p.read_text())["last_run"] == datetime.date.today().isoformat()

    # 3. the gate. Source register stub: one human_fetch source, due in the future
    reg = tmp / "sources.json"
    base = {"publisher": "p", "probe": "x", "held_period": "1", "held_retrieved": "2026-01-01",
            "targets": [], "multi_stage": False, "final_tell": None, "apply": False}

    def write_reg(due):
        reg.write_text(json.dumps([{**base, "id": "hf", "human_fetch": True, "due": due},
                                   {**base, "id": "mach", "human_fetch": False, "due": None}]), encoding="utf-8")
    write_reg("2027-07-31")

    def run_gate(**receipt):
        r = tmp / "r.json"
        r.write_text(json.dumps({"last_run": "2026-11-12", "unresolved": [], "broken_claims": [],
                                 "deferred": [], **receipt}), encoding="utf-8")
        return gate.check_refresh_receipt(r, TODAY, reg)

    rows, problems = run_gate()
    assert problems == [] and rows[0][3] == "ok", (rows, problems)
    # dead-man's switch: 8 days is fine, 9 is not, missing is not, garbage is not, future is not
    assert run_gate(last_run="2026-11-04")[1] == []
    probs = run_gate(last_run="2026-11-03")[1]
    assert len(probs) == 1 and "dead-man" in probs[0][1].lower(), probs
    probs = run_gate(last_run="2026-10-13")[1]
    assert len(probs) == 1 and "30 days" in probs[0][1], probs
    missing = gate.check_refresh_receipt(tmp / "nope.json", TODAY, reg)[1]
    assert len(missing) == 1 and "missing" in missing[0][1].lower() and "dead-man" in missing[0][1].lower()
    (tmp / "bad.json").write_text("{not json", encoding="utf-8")
    assert "dead-man" in gate.check_refresh_receipt(tmp / "bad.json", TODAY, reg)[1][0][1].lower()
    for bad in ("tomorrow", None, 5, "2026-11-13"):
        assert run_gate(last_run=bad)[1], bad
    # unresolved and broken claims fail, each with its own message
    probs = run_gate(unresolved=["census_acs1_ma_income"])[1]
    assert len(probs) == 1 and "census_acs1_ma_income" in probs[0][1]
    probs = run_gate(broken_claims=["c1"])[1]
    assert len(probs) == 1 and "c1" in probs[0][1]
    # deferred (BEA this pass) does NOT fail the gate
    assert run_gate(deferred=["bea_rpp_state"])[1] == []
    # a receipt with the keys missing is a failure, not a pass
    (tmp / "r.json").write_text(json.dumps({"last_run": "2026-11-12"}), encoding="utf-8")
    assert gate.check_refresh_receipt(tmp / "r.json", TODAY, reg)[1]
    # overdue human_fetch: computed from the register at gate time, so it clears the day the due date moves
    write_reg("2026-11-11")
    probs = run_gate()[1]
    assert len(probs) == 1 and "hf" in probs[0][1] and "2026-11-11" in probs[0][1], probs
    write_reg("2026-11-12")
    assert run_gate()[1] == []          # due today is not yet overdue
    write_reg(None)
    assert "no due date" in run_gate()[1][0][1]
    write_reg("2027-07-31")

    # 4. runner.run: the decision logic, with stub fetch/apply
    sources = load_sources(REPO / "data" / "sources.json")
    acs = next(s for s in sources if s.id == "census_acs1_ma_income")
    bea = next(s for s in sources if s.id == "bea_rpp_state")
    doi = next(s for s in sources if s.id == "doi_merged_market_rates")
    acs, bea = dataclasses.replace(acs, held_period="2024"), dataclasses.replace(bea, held_period="2024")
    doi_past = dataclasses.replace(doi, due="2026-01-01")
    claims = load_claims(REPO / "data" / "claims.json")
    OKROW = json.dumps([["NAME", "B19113_001E", "B19013_001E", "state"], ["Massachusetts", "1", "2", "25"]])

    def fetch(url):
        if "census.gov" in url:
            if "/2025/" in url:
                return OKROW
            raise NotFound(url)
        if "bea.gov" in url:
            return "<p>The highest RPPs in 2025 were</p>"
        raise AssertionError(url)

    def run(srcs, apply_fn):
        return runner.run(srcs, claims, fetch=fetch, apply_fn=apply_fn, today="2026-11-12")

    ok_apply = lambda m: acs_applied

    def failing_apply(m):
        raise runner.FetchError("short response")
    rec = run([acs, bea, doi_past], ok_apply)
    assert [a.source_id for a in rec.applied] == ["census_acs1_ma_income"]
    assert [m.source_id for m in rec.deferred] == ["bea_rpp_state"]        # apply:false moved: deferred
    assert rec.unresolved == [] and [k.source_id for k in rec.overdue] == ["doi_merged_market_rates"]
    rec = run([acs, bea, doi], failing_apply)
    assert [u.source_id for u in rec.unresolved] == ["census_acs1_ma_income"]   # apply:true moved, not fetched
    assert "short response" in rec.unresolved[0].error and rec.applied == []
    assert [m.source_id for m in rec.deferred] == ["bea_rpp_state"] and rec.overdue == []
    # an exception chain is never carried: the error is a plain str
    assert all(type(u.error) is str for u in rec.unresolved)
    # a quiet run: held == newest everywhere, DOI not due
    acs25 = dataclasses.replace(acs, held_period="2025")
    bea25 = dataclasses.replace(bea, held_period="2025")
    rec = run([acs25, bea25, doi], ok_apply)
    assert format_message(rec) is None, format_message(rec)

    # probe failure on apply:true -> unresolved (gate); on apply:false -> reported, not gating
    def dead(url):
        raise OSError("unreachable")
    rec = runner.run([acs25, bea25, doi], claims, fetch=dead, apply_fn=ok_apply, today="2026-11-12")
    # EVERY probe failure is unresolved, including on an apply:false source like BEA.
    # It used to split by the apply flag and park the apply:false half in probe_failures,
    # which the gate never read -- so a reworded BEA page produced a green run.
    assert sorted(u.source_id for u in rec.unresolved) == ["bea_rpp_state", "census_acs1_ma_income"]
    # claims: `known` is built from the real registries; a typo'd figure id in a claim raises
    try:
        runner.run([acs25, bea25, doi], claims + [Claim(id="typo", figures=["ma_auto_expendature"])],
                   fetch=fetch, apply_fn=ok_apply, today="2026-11-12")
        raise SystemExit("FAIL: typo'd figure id passed as known")
    except UnknownFigure as e:
        assert "ma_auto_expendature" in str(e), e
    # a moved source under a no-relation claim surfaces as suspect; unmoved relation claims stay quiet
    rec = run([acs, bea25, doi], ok_apply)
    assert [v.claim_id for v in rec.verdicts if v.status == "suspect"] == ["ma_median_household_income"], rec.verdicts

    # 5. main: a real (non-dry) run writes the receipt and prints the message; a dry run writes neither
    r = tmp / "main-receipt.json"
    regp = tmp / "main-reg.json"
    regp.write_text(json.dumps([dataclasses.asdict(s) for s in (acs25, bea25, doi)]), encoding="utf-8")
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = runner.main(["--register", str(regp), "--receipt", str(r)], fetch=fetch)
    assert rc == 0 and r.exists() and buf.getvalue() == "", (rc, buf.getvalue())   # quiet run: receipt, no message
    assert json.loads(r.read_text())["unresolved"] == []
    r.unlink()
    with redirect_stdout(io.StringIO()):
        runner.main(["--dry-run", "--register", str(regp), "--receipt", str(r)], fetch=fetch)
    assert not r.exists()
    regp.write_text(json.dumps([dataclasses.asdict(s) for s in (acs25, bea, doi)]), encoding="utf-8")   # BEA moved, apply:false
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = runner.main(["--register", str(regp), "--receipt", str(r)], fetch=fetch)
    assert rc == 0 and "DEFERRED" in buf.getvalue() and json.loads(r.read_text())["deferred"] == ["bea_rpp_state"]

    # 6. no production code serialises an exception chain.
    # Parsed, not grepped: a comment EXPLAINING why we never touch __context__ is not a
    # violation, and a source-text grep cannot tell the two apart. It flagged the comment
    # on the fix that made __context__ None in the first place.
    import ast
    BANNED = {"format_exception", "format_exc", "print_exc", "exc_info", "__context__", "__cause__"}
    for f in ("report.py", "runner.py", "probes.py"):
        tree = ast.parse((REPO / "scripts" / "refresh" / f).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in BANNED, (f, node.attr, node.lineno)
            elif isinstance(node, ast.Name):
                assert node.id not in BANNED, (f, node.id, node.lineno)
except Exception as e:
    import traceback
    traceback.print_exc()
    print("FAIL", type(e).__name__, e)
    sys.exit(1)
print("PASS test-refresh-report")
