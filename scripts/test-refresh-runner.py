"""Runner tests. Prints and exits 0 on pass, 1 on fail. Stdlib only, no network."""
import dataclasses
import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.refresh.register import load_sources
from scripts.refresh.probes import ProbeError, NotFound
from scripts.refresh import runner
from scripts.refresh.runner import survey, Move

by_id = {s.id: s for s in load_sources(REPO / "data" / "sources.json")}
acs, bea, doi = (by_id[k] for k in ("census_acs1_ma_income", "bea_rpp_state", "doi_merged_market_rates"))

OK = json.dumps([["NAME", "B19113_001E", "B19013_001E", "state"],
                 ["Massachusetts", "120000", "99000", "25"]])


def stub_census(years):
    def fetch(url):
        yr = int(url.split("/data/")[1].split("/")[0])
        if yr not in years:
            raise NotFound(url)
        return years[yr]
    return fetch


def stub_doi(carriers):
    rows = "".join(f"<tr><td>Carrier {i}</td><td>5%</td></tr>" for i in range(carriers))
    page = f"<h2>Final Merged Market Rates</h2><table>{rows}</table>"
    def fetch(url):
        if "info-details/2027-" not in url:
            raise NotFound(url)
        return page
    return fetch


def bea_page(year):
    return f"<p>The highest RPPs in {year} were</p>"


def router(**by_host):
    """fetch that dispatches on a substring of the URL; unknown hosts fail loudly."""
    def fetch(url):
        for key, f in by_host.items():
            if key in url:
                return f(url)
        raise AssertionError(f"unexpected fetch {url}")
    return fetch


def raises_conn(url):
    raise OSError("unreachable")


try:
    acs_held_2024 = dataclasses.replace(acs, held_period="2024")
    acs_held_2025 = dataclasses.replace(acs, held_period="2025")
    doi_held_2026 = dataclasses.replace(doi, held_period="2026", human_fetch=False)

    bea_held_2024 = dataclasses.replace(bea, held_period="2024")
    r = survey([acs_held_2024], fetch=stub_census({2025: OK}))
    moves = r.moves
    assert len(moves) == 1 and moves[0].newest == "2025", moves
    assert moves[0] == Move("census_acs1_ma_income", "2024", "2025", True, moves[0].evidence_url)
    assert "/2025/" in moves[0].evidence_url
    assert r.failures == [] and r.skipped == []

    # held == newest is silence, not a move
    r = survey([acs_held_2025], fetch=stub_census({2025: OK}))
    assert r.moves == [] and r.failures == [], r

    # stage-one move is reported, marked not-final
    moves = survey([doi_held_2026], fetch=stub_doi(carriers=7)).moves
    assert len(moves) == 1 and moves[0].is_final is False and moves[0].newest == "2027", moves

    # decision 1: human_fetch sources are never probed
    def boom(url):
        raise AssertionError(f"probed a human_fetch source: {url}")
    assert doi.human_fetch
    r = survey([doi], fetch=boom)
    assert r.moves == [] and r.failures == [], r
    assert [(k.source_id, k.due, k.held_period) for k in r.skipped] ==         [("doi_merged_market_rates", "2027-07-31", "2027")], r.skipped
    # the result is not a container: no silent "all clear" via truthiness or iteration
    for bad in (lambda: len(r), lambda: bool(r) and iter(r), lambda: r[0]):
        try:
            bad()
        except TypeError:
            pass
        else:
            raise AssertionError("SurveyResult behaves like a container")

    # decision 2: one ProbeError does not blind the survey; it is recorded
    fetch = router(**{"api.census.gov": raises_conn, "bea.gov": lambda u: bea_page(2026)})
    r = survey([acs_held_2024, bea_held_2024, doi], fetch=fetch)
    moves = r.moves
    assert [m.source_id for m in moves] == ["bea_rpp_state"], moves
    assert moves[0].held == "2024" and moves[0].newest == "2026"
    assert len(r.failures) == 1 and r.failures[0].source_id == "census_acs1_ma_income"
    assert "unreachable" in r.failures[0].error

    # order: a failure first, a move after, both survive
    r = survey([bea_held_2024, acs_held_2024], fetch=router(**{
        "bea.gov": lambda u: bea_page(2024), "api.census.gov": stub_census({2025: OK})}))
    assert [m.source_id for m in r.moves] == ["census_acs1_ma_income"] and r.failures == []

    # main --dry-run prints a line per source, writes nothing, exit 0 when clean
    import tempfile
    reg = Path(tempfile.mkdtemp()) / "sources.json"
    reg.write_text(json.dumps([
        {**dataclasses.asdict(s)} for s in (acs_held_2025, bea_held_2024, doi)]), encoding="utf-8")
    before = reg.read_bytes()
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = runner.main(["--dry-run", "--register", str(reg)], fetch=router(**{
            "api.census.gov": stub_census({2025: OK}), "bea.gov": lambda u: bea_page(2024)}))
    out = buf.getvalue()
    assert rc == 0, (rc, out)
    assert "census_acs1_ma_income" in out and "bea_rpp_state" in out
    assert "doi_merged_market_rates" in out and "skipped" in out.lower()
    assert reg.read_bytes() == before

    # failures show in output and make the exit code nonzero
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = runner.main(["--dry-run", "--register", str(reg)], fetch=router(**{
            "api.census.gov": raises_conn, "bea.gov": lambda u: bea_page(2024)}))
    assert rc == 1 and "FAILED" in buf.getvalue() and "census_acs1_ma_income" in buf.getvalue()

    # (without --dry-run main now runs for real and writes the receipt: see test-refresh-report.py)
    # ---------------- Task 4: apply (ACS only; writes published files) ----------------
    import os
    import shutil
    from scripts.refresh.runner import apply, FetchError, Applied, Conflict, pull_and_recheck

    os.environ["CENSUS_API_KEY"] = "test-key"
    TODAY = "2026-11-12"
    acs_move = Move("census_acs1_ma_income", "2024", "2025", True, "https://api.census.gov/data/2025/acs/acs1")
    TARGETS = ["affordability-dashboard.html", "data/burden-constants.json", "data/cost-of-living-latest.json"]
    assert load_sources(REPO / "data" / "sources.json")[0].targets == TARGETS, "register must list all three holders"
    assert len(runner.STATES) == 51 and runner.STATES["District of Columbia"] == "DC"

    def blob_income(text):
        m = re.search(r'<script id="col-data" type="application/json">(.*?)</script>', text, re.S)
        return json.loads(m.group(1))["income"]

    REAL_BY_STATE = blob_income((REPO / "affordability-dashboard.html").read_text(encoding="utf-8"))["household_by_state"]

    def make_root(html_eol="\n", json_eol="\r\n"):
        """Temp repo root holding copies of the real targets, with forced line endings."""
        root = Path(tempfile.mkdtemp())
        (root / "data").mkdir()
        shutil.copy(REPO / "data" / "sources.json", root / "data" / "sources.json")
        for rel, eol in zip(TARGETS, (html_eol, json_eol, json_eol)):
            t = (REPO / rel).read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\n", eol)
            (root / rel).parent.mkdir(exist_ok=True)
            (root / rel).write_bytes(t.encode("utf-8"))
        return root

    def snap(root):
        return {rel: (root / rel).read_bytes() for rel in TARGETS}

    def stub_census_full(ma_hh=106539, ma_fam=138434, us=84780, bump=0, n=None, drop=(), seen=None):
        vals = {a: v + bump for a, v in REAL_BY_STATE.items()}
        vals["DC"] = 99000 + bump
        vals["MA"] = ma_hh
        rows = [["NAME", "B19013_001E", "state"]]
        for name, ab in runner.STATES.items():
            if ab not in drop:
                rows.append([name, str(int(vals[ab])), "00"])
        if n is not None:
            rows = rows[:1] + rows[1:][:n]
        def fetch(url):
            if seen is not None:
                seen.append(url)
            assert "key=test-key" in url, url
            if "for=state:25" in url:
                return json.dumps([["NAME", "B19113_001E", "B19013_001E", "state"],
                                   ["Massachusetts", str(ma_fam), str(ma_hh), "25"]])
            if "for=state:*" in url:
                return json.dumps(rows)
            if "for=us:1" in url:
                return json.dumps([["NAME", "B19013_001E", "us"], ["United States", str(us), "1"]])
            raise AssertionError(f"unexpected fetch {url}")
        return fetch

    # a stale root: apply a 2024 release first (setup only; the result is asserted in test 1)
    def stale_root(**kw):
        root = make_root(**kw)
        apply(dataclasses.replace(acs_move, held="2023", newest="2024"), root=root, today="2026-01-01",
              fetch=stub_census_full(ma_hh=104828, ma_fam=134000, us=80000, bump=-2000))
        return root

    # 0. a no-op apply is a genuine no-op: same bytes, nothing written, nothing divergent
    root = make_root()
    before = snap(root)
    a = apply(dataclasses.replace(acs_move, held="2025"), fetch=stub_census_full(), root=root, today=TODAY)
    assert isinstance(a, Applied) and a.files_written == [] and a.divergences == [], a
    assert snap(root) == before
    assert a.new["household"] == 106539.0 and a.new["vintage"] == 2025 and a.old == a.new

    # 1. brief happy path: stale files move to 2025, both written, vintage consistent
    root = stale_root()
    assert blob_income((root / TARGETS[0]).read_text(encoding="utf-8"))["vintage"] == 2024
    seen = []
    a = apply(acs_move, fetch=stub_census_full(seen=seen), root=root, today=TODAY)
    assert a.new["household"] == 106539.0 and a.new["vintage"] == 2025
    assert set(a.files_written) == set(TARGETS), a.files_written
    assert a.old["vintage"] == 2024 and a.old["household"] == 104828.0
    assert a.divergences == []
    assert all("/data/2025/" in u for u in seen) and len(seen) == 3
    for rel in TARGETS:
        assert "test-key" not in (root / rel).read_text(encoding="utf-8"), "API key leaked into a published file"
    inc = blob_income((root / TARGETS[0]).read_text(encoding="utf-8"))
    assert inc["household"] == 106539.0 and inc["family"] == 138434.0 and inc["vintage"] == 2025
    assert inc["household_by_state"] == REAL_BY_STATE and inc["household_us"] == 84780.0
    assert "DC" not in inc["household_by_state"], "shape changed: the map holds 50 states"
    assert inc["household_by_state_retrieved"] == TODAY
    bc = json.loads((root / TARGETS[1]).read_text(encoding="utf-8"))["states"]["MA"]["acs"]["medianHouseholdIncome_ACS"]
    assert bc["value"] == 106539 and "2025" in bc["source"] and bc["verified"] == TODAY
    # moving stale -> 2025 reproduces the live files except the date stamps
    for rel in TARGETS:
        live = (REPO / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
        got = (root / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
        a_l, b_l = live.splitlines(), got.splitlines()
        assert len(a_l) == len(b_l) and sum(x != y for x, y in zip(a_l, b_l)) <= 2, rel

    # 2. line endings survive exactly, and the diff is confined to the figure
    for html_eol, json_eol in (("\n", "\r\n"), ("\r\n", "\n")):
        root = stale_root(html_eol=html_eol, json_eol=json_eol)
        before = snap(root)
        apply(acs_move, fetch=stub_census_full(), root=root, today=TODAY)
        after = snap(root)
        for rel, eol in zip(TARGETS, (html_eol, json_eol, json_eol)):
            assert after[rel] != before[rel]
            bad = (after[rel].count(b"\n") - after[rel].count(b"\r\n")) if eol == "\r\n" else after[rel].count(b"\r")
            assert bad == 0, f"{rel}: line endings changed"
            assert after[rel].count(b"\n") == before[rel].count(b"\n"), rel
        # HTML: only the income object differs; everything around it is byte-identical
        pre = lambda b: b[:b.index(b'"income":')]
        post = lambda b: b[b.index(b"</script>", b.index(b'"income":')):]
        assert pre(after[TARGETS[0]]) == pre(before[TARGETS[0]]) and post(after[TARGETS[0]]) == post(before[TARGETS[0]])
        # JSON: at most 4 lines (value, source, url, verified)
        la, lb = before[TARGETS[1]].split(json_eol.encode()), after[TARGETS[1]].split(json_eol.encode())
        assert len(la) == len(lb) and sum(x != y for x, y in zip(la, lb)) <= 4
        lc, ld = before[TARGETS[2]].split(json_eol.encode()), after[TARGETS[2]].split(json_eol.encode())
        i0 = next(i for i, x in enumerate(lc) if x.startswith(b' "income"'))
        assert len(lc) == len(ld) and lc[:i0] == ld[:i0], "cost-of-living feed: diff leaked outside income"
        assert not after[TARGETS[2]].endswith(b"\n"), "cost-of-living feed gained a trailing newline"

    # 3. Review Focus 2: a short or partial response aborts the WHOLE write
    root = stale_root()
    before = snap(root)
    def null_cell(url):
        t = stub_census_full()(url)
        return t.replace('"Alabama", "67663"', '"Alabama", null') if "state:*" in url else t
    def ma_disagree(url):  # the MA call and the map must come from one release
        t = stub_census_full()(url)
        return t.replace('"106539"', '"106540"') if "state:25" in url else t
    def junk(url):
        return "<html>rate limited</html>"
    def down(url):
        raise OSError("unreachable")
    bad_fetches = {"12 states": stub_census_full(n=12), "no DC": stub_census_full(drop=("DC",)),
                   "one missing": stub_census_full(drop=("WY",)), "null cell": null_cell,
                   "MA mismatch": ma_disagree, "not json": junk, "unreachable": down}
    for label, f in bad_fetches.items():
        try:
            apply(acs_move, fetch=f, root=root, today=TODAY)
            assert False, f"{label}: bad response was written"
        except FetchError:
            pass
        assert snap(root) == before, f"{label}: a failed fetch modified a file"
    # the API key must never surface in an error: urlopen_text raises NotFound with the KEYED url
    import traceback
    os.environ["CENSUS_API_KEY"] = "SECRET123"
    def keyed_404(url):
        raise NotFound(url)
    def keyed_oserror(url):
        raise OSError(f"connection reset for {url}")
    def keyed_late(url):  # the second and third calls fail, after the first succeeded
        if "state:25" in url:
            return json.dumps([["NAME", "B19113_001E", "B19013_001E", "state"], ["Massachusetts", "138434", "106539", "25"]])
        raise NotFound(url)
    try:
        for f in (keyed_404, keyed_oserror, keyed_late):
            for dry in (False, True):
                try:
                    apply(acs_move, fetch=f, root=root, today=TODAY, dry=dry)
                    assert False, "keyed failure not raised"
                except FetchError as e:
                    shown = "".join(traceback.format_exception(e))  # text AND chained causes
                    assert "SECRET123" not in shown, f"API key in error text: {shown}"
                    assert "api.census.gov" in str(e)
    finally:
        os.environ["CENSUS_API_KEY"] = "test-key"
    assert snap(root) == before
    saved = os.environ.pop("CENSUS_API_KEY")
    try:
        apply(acs_move, fetch=boom, root=root, today=TODAY)
        assert False, "keyless apply ran"
    except FetchError:
        pass
    finally:
        os.environ["CENSUS_API_KEY"] = saved
    assert snap(root) == before
    # a register missing a required target names it instead of a bare KeyError
    regs = json.loads((root / "data" / "sources.json").read_text(encoding="utf-8"))
    regs[0]["targets"] = regs[0]["targets"][1:]
    (root / "data" / "sources.json").write_text(json.dumps(regs), encoding="utf-8")
    try:
        apply(acs_move, fetch=stub_census_full(), root=root, today=TODAY)
        assert False
    except ValueError as e:
        assert "affordability-dashboard.html" in str(e), e
    assert snap(root) == before
    shutil.copy(REPO / "data" / "sources.json", root / "data" / "sources.json")
    # only ACS is applied in this task
    try:
        apply(Move("bea_rpp_state", "2024", "2025", True, "x"), fetch=boom, root=root)
        assert False, "applied a BEA move"
    except ValueError:
        pass

    # 4. dry run fetches and validates but writes nothing
    a = apply(acs_move, fetch=stub_census_full(), root=root, today=TODAY, dry=True)
    assert a.files_written == [] and snap(root) == before and a.new["vintage"] == 2025
    try:
        apply(acs_move, fetch=stub_census_full(n=12), root=root, today=TODAY, dry=True)
        assert False
    except FetchError:
        pass

    # 5. reconcile: the real bug (two files, two figures) is repaired
    root = make_root()
    t = (root / TARGETS[1]).read_bytes().decode("utf-8")
    assert t.count('"value": 106539,') == 1
    (root / TARGETS[1]).write_bytes(t.replace('"value": 106539,', '"value": 104828,').encode("utf-8"))
    a = apply(dataclasses.replace(acs_move, held="2025"), fetch=stub_census_full(), root=root, today=TODAY)
    assert a.files_written == [TARGETS[1]] and a.divergences == [], a
    # ... and a target that still disagrees after the write is REPORTED, not hidden
    real_write = runner._write_text
    for bad in TARGETS[1:]:
        root = stale_root()
        def lying_write(path, text, bad=bad):
            real_write(path, text.replace("106539", "104828") if path.name == Path(bad).name else text)
        runner._write_text = lying_write
        try:
            a = apply(acs_move, fetch=stub_census_full(), root=root, today=TODAY)
        finally:
            runner._write_text = real_write
        assert a.divergences == [bad], (bad, a.divergences)

    # 5b. the cost-of-living feed is the file update-cost-of-living.py rebuilds the HTML from.
    # Left stale, the next scheduled run would revert the page. It must be detected AND corrected.
    root = make_root()
    donor = stale_root()
    (root / TARGETS[2]).write_bytes((donor / TARGETS[2]).read_bytes())  # html + burden current, feed stale
    assert json.loads((root / TARGETS[2]).read_text(encoding="utf-8"))["income"]["vintage"] == 2024
    # (a) detected: a dry run writes nothing but reports the disagreeing target
    pre = snap(root)
    a = apply(dataclasses.replace(acs_move, held="2025"), fetch=stub_census_full(), root=root, today=TODAY, dry=True)
    assert a.divergences == [TARGETS[2]] and a.files_written == [] and snap(root) == pre, a
    # (b) corrected: only the stale feed is written, and all three now agree
    a = apply(dataclasses.replace(acs_move, held="2025"), fetch=stub_census_full(), root=root, today=TODAY)
    assert a.files_written == [TARGETS[2]] and a.divergences == [], a
    assert snap(root)[TARGETS[0]] == pre[TARGETS[0]] and snap(root)[TARGETS[1]] == pre[TARGETS[1]]
    feed = json.loads((root / TARGETS[2]).read_text(encoding="utf-8"))["income"]
    assert (feed["household"], feed["family"], feed["vintage"]) == (106539.0, 138434.0, 2025)
    assert feed == blob_income((root / TARGETS[0]).read_text(encoding="utf-8")) or \
        {k: v for k, v in feed.items() if k != "household_by_state_retrieved"} == \
        {k: v for k, v in blob_income((root / TARGETS[0]).read_text(encoding="utf-8")).items()
         if k != "household_by_state_retrieved"}, "feed and page income blocks differ"
    # (c) the rest of the feed (RPP, metros, living wage) is untouched, key order kept
    live = json.loads((REPO / TARGETS[2]).read_text(encoding="utf-8"))
    got = json.loads((root / TARGETS[2]).read_text(encoding="utf-8"))
    assert {k: v for k, v in got.items() if k != "income"} == {k: v for k, v in live.items() if k != "income"}
    assert list(got["income"]) == list(live["income"]) and list(got) == list(live)

    # 5c. a target whose source string disagrees is reported even when every number matches
    root = make_root()
    f2 = root / TARGETS[2]
    f2.write_bytes(f2.read_bytes().replace(b"Census ACS 1-Year 2025", b"Census ACS 1-Year 2024"))
    a = apply(dataclasses.replace(acs_move, held="2025"), fetch=stub_census_full(), root=root, today=TODAY, dry=True)
    assert a.divergences == [TARGETS[2]], a.divergences

    # 6. a write that fails midway restores the files already written
    root = stale_root()
    before = snap(root)
    calls = []
    def flaky_write(path, text):
        calls.append(path.name)
        if len(calls) == 2:
            raise OSError("disk full")
        real_write(path, text)
    runner._write_text = flaky_write
    try:
        apply(acs_move, fetch=stub_census_full(), root=root, today=TODAY)
        assert False, "write failure swallowed"
    except OSError:
        pass
    finally:
        runner._write_text = real_write
    assert snap(root) == before, "a half-finished write was left on disk"

    # 7. Review Focus 3: concurrent sessions. Pull, then re-verify; never real git, never the network
    root = make_root()
    gitlog = []
    ok_git = lambda args, cwd: gitlog.append((args, cwd))
    a = apply(dataclasses.replace(acs_move, held="2025"), fetch=stub_census_full(), root=root, today=TODAY)
    def set_held(p):
        regs = json.loads((root / "data" / "sources.json").read_text(encoding="utf-8"))
        for e in regs:
            if e["id"] == "census_acs1_ma_income":
                e["held_period"] = p
        (root / "data" / "sources.json").write_text(json.dumps(regs), encoding="utf-8")
    set_held("2024")
    assert pull_and_recheck(a, acs_move, fetch=stub_census({2025: OK}), root=root, git=ok_git) == []
    assert gitlog and gitlog[0][0][:2] == ["pull", "--rebase"], gitlog
    set_held("2025")  # another session already applied this move and bumped the register
    try:
        pull_and_recheck(a, acs_move, fetch=stub_census({2025: OK}), root=root, git=ok_git)
        assert False, "held value changed underneath but was not caught"
    except Conflict:
        pass
    set_held("2024")  # publisher no longer shows the move
    try:
        pull_and_recheck(a, acs_move, fetch=stub_census({2024: OK}), root=root, git=ok_git)
        assert False
    except Conflict:
        pass
    def bad_git(args, cwd):
        raise RuntimeError("rebase conflict")
    try:
        pull_and_recheck(a, acs_move, fetch=boom, root=root, git=bad_git)
        assert False
    except Conflict:
        pass
except AssertionError as e:
    print("FAIL", e)
    sys.exit(1)
print("PASS test-refresh-runner")
