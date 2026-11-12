"""Probes: ask each publisher what its newest edition is.

Contract: a probe that cannot reach or parse its publisher RAISES ProbeError.
It never returns a result meaning "nothing new". Only an HTTP 404 for a year
that is not published yet is a normal negative (the walk continues).
"""
import datetime
import html
import json
import os
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
        if e.code != 404:
            raise
    # Only a 404 falls through to here -- the try returns on success, and any other
    # error re-raised above. Raised OUTSIDE the except block on purpose: `from e` would
    # leave the HTTPError on __context__, and HTTPError.url carries the KEYED url even
    # when str() and format_exception() are clean.
    raise NotFound(url)


def _get(fetch, url, key=None):
    """fetch(url) with every failure but NotFound converted to ProbeError.

    `key`, when given, is appended to the REQUEST only. Every message built here names the
    key-free `url`, and the keyed text is scrubbed out of anything the fetcher said: an
    exception's text and chain are what reach the public Actions log.
    """
    req = url if key is None else f"{url}&key={key}"
    clean = (lambda t: str(t).replace(key, "***")) if key else str
    try:
        return fetch(req)
    except NotFound:
        miss = True
    except Exception as e:  # unreachable, 403/5xx, timeout, bad decode: all unanswerable
        miss, why = False, f"{type(e).__name__}: {clean(e)}"
    # raised OUTSIDE the except block so no keyed exception rides along on __context__
    if miss:
        raise NotFound(url)
    raise ProbeError(f"{url}: {why}")


def _walk(fetch, years, url_for, key=None):
    """First year whose page exists, newest first. Returns (year, url, body); url is key-free."""
    for yr in years:
        url = url_for(yr)
        try:
            return yr, url, _get(fetch, url, key)
        except NotFound:
            continue
    raise ProbeError(f"nothing published in {years[0]}..{years[-1]}: cannot tell what is newest")


def _census_acs1(source, fetch):
    # Same source as runner.apply (os.environ, set from the repo secret in CI). The refresh-burden-acs.py
    # .env fallback is for one-off local runs and crashes when .env is absent; a probe must raise ProbeError.
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        # Keyless, Census answers HTTP 200 with an HTML "Missing Key" page: never send one and read it.
        raise ProbeError("CENSUS_API_KEY is not set: the Census API refuses keyless requests")
    this = datetime.date.today().year
    yr, url, body = _walk(
        fetch, range(this, this - WALK, -1),
        lambda y: f"https://api.census.gov/data/{y}/acs/acs1?get=NAME,B19113_001E,B19013_001E&for=state:25",
        key)
    try:
        head, row = json.loads(body)[:2]
        name, income = row[head.index("NAME")], row[head.index("B19013_001E")]
        why = None
    except Exception as e:
        # JSONDecodeError keeps the whole response body on .doc, so it must not survive as
        # __cause__ or __context__: record the text, raise after the except block.
        name = income = None
        why = f"unreadable Census response ({type(e).__name__})"
    if why:
        raise ProbeError(f"{url}: {why}")
    if name != "Massachusetts" or not income:
        raise ProbeError(f"{url}: Census response is not Massachusetts income ({name!r}, {income!r})")
    return Probe(str(yr), True, url)


def _bea_rpp(source, fetch):
    url = "https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area"
    text = html.unescape(re.sub(r"<[^>]+>", " ", _get_required(fetch, url)))
    # ponytail: keyed on the page's "highest RPPs in YYYY" sentence; raises if BEA rewords it
    years = re.findall(r"highest\s+RPPs?\s+in\s+(20\d\d)", text, re.I)
    if not years:
        raise ProbeError(f"{url}: no 'highest RPPs in <year>' sentence found")
    best = max(years)
    # prose can mention an earlier year first; a result older than what we already hold is a misread
    if source.held_period.isdigit() and int(best) < int(source.held_period):
        raise ProbeError(f"{url}: newest 'highest RPPs in' year is {best}, older than the held {source.held_period}")
    return Probe(best, True, url)


def _get_required(fetch, url):
    try:
        return _get(fetch, url)
    except NotFound as e:  # a fixed page that 404s is not "year not published"
        raise ProbeError(f"{url}: page not found") from e


_FINAL = re.compile(r"final\s+merged\s+market\s+rates", re.I)


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _final_table_carriers(page, url):
    """Carrier rows in the table headed 'Final Merged Market Rates'.

    Reads the table and its own heading/caption only, never the prose around it.
    Raises ProbeError if there is no such table or it yields no carrier rows:
    a reworded heading must not look like a pre-final page.
    """
    parts = re.split(r"(?i)<table\b", page)
    if len(parts) < 2:
        raise ProbeError(f"{url}: no tables on page, cannot count carriers")
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
        if n == 0:
            raise ProbeError(f"{url}: Final table found but no carrier rows parsed")
        return n
    raise ProbeError(f"{url}: no table headed 'Final Merged Market Rates'")


def _doi_rates(source, fetch):
    nxt = datetime.date.today().year + 1
    yr, url, page = _walk(fetch, range(nxt, nxt - WALK, -1),
                          lambda y: f"https://www.mass.gov/info-details/{y}-health-insurance-rates")
    n = _final_table_carriers(page, url)
    # register final_tell: eight carriers in the Final table; fewer is stage one
    return Probe(str(yr), n >= 8, url)


_PROBES = {"census_acs1": _census_acs1, "bea_rpp": _bea_rpp, "doi_rates": _doi_rates}


def probe(source: Source, *, fetch=urlopen_text) -> Probe:
    try:
        fn = _PROBES[source.probe]
    except KeyError:
        raise ProbeError(f"{source.id}: unknown probe {source.probe!r}") from None
    return fn(source, fetch)
