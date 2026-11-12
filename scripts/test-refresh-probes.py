"""Probe tests. Prints and exits 0 on pass, 1 on fail. Stdlib only, no network."""
import json
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.refresh.register import load_sources
from scripts.refresh.probes import probe, ProbeError, NotFound, Probe

by_id = {s.id: s for s in load_sources(REPO / "data" / "sources.json")}
acs, bea, doi = (by_id[k] for k in ("census_acs1_ma_income", "bea_rpp_state", "doi_merged_market_rates"))

OK = json.dumps([["NAME", "B19113_001E", "B19013_001E", "state"],
                 ["Massachusetts", "120000", "99000", "25"]])
NOT_FOUND = None


def stub_census(years):
    """years: {year: OK | NOT_FOUND | other body}. Unlisted years are 404."""
    def fetch(url):
        yr = int(url.split("/data/")[1].split("/")[0])
        body = years.get(yr, NOT_FOUND)
        if body is NOT_FOUND:
            raise NotFound(url)
        return body
    return fetch


def stub_doi(carriers, years=None, prose="currently reviewing and will culminate in a final decision in August"):
    rows = "".join(f"<tr><td>Carrier {i}</td><td>5.1%</td></tr>" for i in range(carriers))
    page = (f"<h2>Overview</h2><p>{prose}</p>"
            f"<h2>Final Merged Market Rates</h2><table><tr><th>Carrier</th><th>Rate</th></tr>{rows}"
            f"<tr><td>Total</td><td>5%</td></tr></table>")
    def fetch(url):
        yr = int(url.split("info-details/")[1][:4])
        if years is not None and yr not in years:
            raise NotFound(url)
        return page
    return fetch


def stub_bea(body):
    return lambda url: body


def raises(src, fetch):
    try:
        probe(src, fetch=fetch)
    except ProbeError:
        return True
    return False


try:
    # newest edition found; walk continues past a 404
    p = probe(acs, fetch=stub_census({2025: OK, 2026: NOT_FOUND}))
    assert isinstance(p, Probe) and p.newest_period == "2025" and p.is_final is True
    assert "/data/2025/acs/acs1" in p.evidence_url
    # a newer year, once published, wins
    assert probe(acs, fetch=stub_census({2025: OK, 2026: OK, 2027: OK})).newest_period >= "2026"

    # an unreachable publisher must RAISE, never return "nothing new"
    def boom(url): raise OSError("name resolution failed")
    assert raises(acs, boom), "unreachable ACS reported a result"
    assert raises(bea, boom), "unreachable BEA reported a result"
    assert raises(doi, boom), "unreachable DOI reported a result"
    # non-404 HTTP failure mid-walk raises rather than skipping to an older year
    import urllib.error
    def e500(url): raise urllib.error.HTTPError(url, 500, "boom", None, None)
    assert raises(acs, e500)
    # garbage 200, and nothing published at all, also raise
    assert raises(acs, stub_census({2025: "<html>maintenance</html>", 2026: NOT_FOUND}))
    assert raises(acs, stub_census({}))
    assert raises(doi, stub_doi(8, years=[]))

    # DOI multi-stage: seven carriers is stage one, eight is final
    assert probe(doi, fetch=stub_doi(carriers=7)).is_final is False
    p = probe(doi, fetch=stub_doi(carriers=8))
    assert p.is_final is True and "health-insurance-rates" in p.evidence_url
    # stale prose above a finished table must not change the answer
    assert probe(doi, fetch=stub_doi(8, prose="we are currently reviewing")).is_final is True
    assert probe(doi, fetch=stub_doi(7, prose="this is the final decision")).is_final is False
    # DOI walk skips a 404 year and reports the year it found
    import datetime
    nxt = datetime.date.today().year + 1
    assert probe(doi, fetch=stub_doi(8, years=[nxt - 1])).newest_period == str(nxt - 1)
    # unparseable DOI page raises
    assert raises(doi, stub_bea("<html><p>Access denied</p></html>"))

    # BEA: newest data year from the product page
    page = "<p>States with the highest RPPs in 2024 were California</p>"
    p = probe(bea, fetch=stub_bea(page))
    assert p.newest_period == "2024" and p.is_final is True
    assert raises(bea, stub_bea("<p>redesigned page</p>"))

    # unknown probe name raises
    import dataclasses
    assert raises(dataclasses.replace(acs, probe="nope"), stub_bea(""))
except AssertionError as e:
    print("FAIL", e)
    sys.exit(1)
print("PASS test-refresh-probes")
