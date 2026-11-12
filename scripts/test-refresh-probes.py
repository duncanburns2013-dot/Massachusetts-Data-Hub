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


import os
os.environ["CENSUS_API_KEY"] = "test-key"
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
    # Important 1: reworded heading / th-only rows are parse failures, not "stage one"
    assert raises(doi, stub_doi(0)), "Final table with no carrier rows read as a result"
    nofinal = "<h2>Rates</h2><table><tr><td>A</td><td>1%</td></tr></table>"
    assert raises(doi, stub_bea(nofinal)), "no Final-headed table read as a result"
    thonly = "<h2>Final Merged Market Rates</h2><table><tr><th>A</th><th>1%</th></tr></table>"
    assert raises(doi, stub_bea(thonly))

    # Important 2: the real urlopen_text maps 404 -> NotFound and nothing else
    import urllib.request, urllib.error, io
    from scripts.refresh import probes as P
    real = urllib.request.urlopen
    def http(code):
        def fake(req, timeout=None): raise urllib.error.HTTPError(req.full_url, code, "x", None, io.BytesIO(b""))
        return fake
    try:
        for code, want in ((404, NotFound), (403, urllib.error.HTTPError), (500, urllib.error.HTTPError)):
            urllib.request.urlopen = http(code)
            try:
                P.urlopen_text("https://example.invalid/x")
                assert False, f"{code} did not raise"
            except NotFound:
                assert want is NotFound, f"{code} mapped to NotFound"
            except urllib.error.HTTPError:
                assert want is not NotFound, f"{code} not mapped to NotFound"
            # end to end through probe(): only 404 is survivable
            if code != 404:
                assert raises(acs, P.urlopen_text) and raises(doi, P.urlopen_text), f"{code} not ProbeError"
    finally:
        urllib.request.urlopen = real

    # Important 3: remaining branches
    def bea404(url): raise NotFound(url)
    assert raises(bea, bea404), "BEA 404 reported a result"
    def e403(url): raise urllib.error.HTTPError(url, 403, "forbidden", None, None)
    assert raises(doi, e403), "DOI 403 reported a result"
    wrong = json.dumps([["NAME", "B19113_001E", "B19013_001E", "state"], ["Alabama", "1", "2", "01"]])
    assert raises(acs, stub_census({2025: wrong, 2026: NOT_FOUND})), "wrong-NAME Census row accepted"
    assert raises(acs, stub_census({2025: json.dumps([["NAME"], ["Massachusetts"]]), 2026: NOT_FOUND}))
    # Census key: sent on the request, never in evidence_url or any exception text
    KEY = "k3y-SECRET-9f2"
    os.environ["CENSUS_API_KEY"] = KEY
    reqs = []
    def spy(url):
        reqs.append(url)
        return stub_census({2025: OK, 2026: NOT_FOUND})(url)
    p = probe(acs, fetch=spy)
    assert reqs and all(u.endswith("&key=" + KEY) for u in reqs), reqs
    assert KEY not in p.evidence_url and KEY not in repr(p), p
    def leaky(url): raise OSError("connect failed for " + url)
    def leaky404(url): raise NotFound(url)
    import urllib.error
    def leaky500(url): raise urllib.error.HTTPError(url, 500, "boom " + url, None, None)
    for f in (leaky, leaky500, stub_census({2025: "<html>Missing Key " + KEY + "</html>", 2026: NOT_FOUND}), leaky404):
        try:
            probe(acs, fetch=f)
            assert False, "no ProbeError"
        except ProbeError as e:
            chain, x = [], e
            while x is not None:  # every attribute, not just str/repr: JSONDecodeError keeps the body on .doc
                chain.append(f"{x!r} {x} {vars(x)!r} {x.args!r}")
                x = x.__cause__ or x.__context__
            assert KEY not in " ".join(chain), chain
            assert e.__cause__ is None and e.__context__ is None, "an exception chain is still attached"
    # a 200 that is not the data is an error, not a negative (what keyless Census returns)
    html200 = "<html><title>Missing Key</title></html>"
    assert raises(acs, stub_census({2025: html200, 2026: html200}))
    assert raises(acs, stub_census({2026: html200, 2025: OK})), "newest vintage's non-JSON 200 was skipped"
    # keyless: ProbeError up front, no request made
    del os.environ["CENSUS_API_KEY"]
    reqs.clear()
    try:
        probe(acs, fetch=spy)
        assert False, "keyless probe did not raise"
    except ProbeError as e:
        assert "CENSUS_API_KEY" in str(e)
    assert reqs == [], reqs
    os.environ["CENSUS_API_KEY"] = KEY
except AssertionError as e:
    print("FAIL", e)
    sys.exit(1)
print("PASS test-refresh-probes")
