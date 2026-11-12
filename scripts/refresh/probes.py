"""Probes: ask each publisher what its newest edition is.

Contract: a probe that cannot reach or parse its publisher RAISES ProbeError.
It never returns a result meaning "nothing new". Only an HTTP 404 for a year
that is not published yet is a normal negative (the walk continues).
"""
import datetime
import html
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from scripts.refresh.register import Source

WALK = 4  # years to look back before concluding the publisher is unanswerable


class ProbeError(Exception):
    """The publisher could not be asked or its answer could not be read."""


class NotFound(Exception):
    """HTTP 404: the edition is not published (yet). The only non-fatal failure."""


@dataclass
class Probe:
    newest_period: str
    is_final: bool
    evidence_url: str


def urlopen_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (data-hub refresh probe)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise NotFound(url) from e
        raise


def _get(fetch, url):
    """fetch(url) with every failure but NotFound converted to ProbeError."""
    try:
        return fetch(url)
    except NotFound:
        raise
    except Exception as e:  # unreachable, 403/5xx, timeout, bad decode: all unanswerable
        raise ProbeError(f"{url}: {type(e).__name__}: {e}") from e


def _walk(fetch, years, url_for):
    """First year whose page exists, newest first. Returns (year, url, body)."""
    for yr in years:
        url = url_for(yr)
        try:
            return yr, url, _get(fetch, url)
        except NotFound:
            continue
    raise ProbeError(f"nothing published in {years[0]}..{years[-1]}: cannot tell what is newest")


def _census_acs1(source, fetch):
    this = datetime.date.today().year
    yr, url, body = _walk(
        fetch, range(this, this - WALK, -1),
        lambda y: f"https://api.census.gov/data/{y}/acs/acs1?get=NAME,B19113_001E,B19013_001E&for=state:25")
    try:
        head, row = json.loads(body)[:2]
        assert row[head.index("NAME")] == "Massachusetts" and row[head.index("B19013_001E")]
    except Exception as e:
        raise ProbeError(f"{url}: unreadable Census response ({e!r})") from e
    return Probe(str(yr), True, url)


def _bea_rpp(source, fetch):
    url = "https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area"
    text = html.unescape(re.sub(r"<[^>]+>", " ", _get_required(fetch, url)))
    # ponytail: keyed on the page's "highest RPPs in YYYY" sentence; raises if BEA rewords it
    m = re.search(r"highest\s+RPPs?\s+in\s+(20\d\d)", text, re.I)
    if not m:
        raise ProbeError(f"{url}: no 'highest RPPs in <year>' sentence found")
    return Probe(m.group(1), True, url)


def _get_required(fetch, url):
    try:
        return _get(fetch, url)
    except NotFound as e:  # a fixed page that 404s is not "year not published"
        raise ProbeError(f"{url}: page not found") from e


_FINAL = re.compile(r"final\s+merged\s+market\s+rates", re.I)


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _final_table_carriers(page):
    """Carrier rows in the table headed 'Final Merged Market Rates'; None if no tables.

    Reads the table and its own heading/caption only, never the prose around it.
    """
    parts = re.split(r"(?i)<table\b", page)
    if len(parts) < 2:
        return None
    for before, tbl in zip(parts, parts[1:]):
        tbl = re.split(r"(?i)</table>", tbl)[0]
        heads = re.findall(r"(?is)<h[1-6]\b.*?</h[1-6]>", before)
        label = _text((heads[-1] if heads else "") + " " + " ".join(re.findall(r"(?is)<caption.*?</caption>", tbl)))
        if not _FINAL.search(label):
            continue
        n = 0
        for tr in re.findall(r"(?is)<tr\b.*?</tr>", tbl):
            cells = re.findall(r"(?is)<td\b.*?</td>", tr)
            first = _text(cells[0]) if cells else ""
            if first and not re.match(r"(?i)(grand\s+)?(total|average|overall|all\s+carriers)", first):
                n += 1
        return n
    return 0


def _doi_rates(source, fetch):
    nxt = datetime.date.today().year + 1
    yr, url, page = _walk(fetch, range(nxt, nxt - WALK, -1),
                          lambda y: f"https://www.mass.gov/info-details/{y}-health-insurance-rates")
    n = _final_table_carriers(page)
    if n is None:
        raise ProbeError(f"{url}: no tables on page, cannot count carriers")
    # register final_tell: eight carriers in the Final table; fewer is stage one
    return Probe(str(yr), n >= 8, url)


_PROBES = {"census_acs1": _census_acs1, "bea_rpp": _bea_rpp, "doi_rates": _doi_rates}


def probe(source: Source, *, fetch=urlopen_text) -> Probe:
    try:
        fn = _PROBES[source.probe]
    except KeyError:
        raise ProbeError(f"{source.id}: unknown probe {source.probe!r}") from None
    return fn(source, fetch)
