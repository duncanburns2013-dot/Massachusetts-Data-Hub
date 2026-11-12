"""Runner tests. Prints and exits 0 on pass, 1 on fail. Stdlib only, no network."""
import dataclasses
import io
import json
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

    # without --dry-run there is nothing to do yet: refuse rather than silently survey
    with redirect_stdout(io.StringIO()):
        rc = runner.main([], fetch=boom)
    assert rc == 2
except AssertionError as e:
    print("FAIL", e)
    sys.exit(1)
print("PASS test-refresh-runner")
