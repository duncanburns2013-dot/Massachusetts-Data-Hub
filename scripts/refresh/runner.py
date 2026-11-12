"""Runner: survey every source for moved publishers; apply() writes ACS figures into the targets."""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.refresh.probes import ProbeError, probe, urlopen_text
from scripts.refresh.claims import evaluate, load_claims
from scripts.refresh.register import Source, load_sources
from scripts.refresh.report import RunRecord, format_message, write_receipt

REGISTER = Path(__file__).resolve().parents[2] / "data" / "sources.json"
CLAIMS = Path(__file__).resolve().parents[2] / "data" / "claims.json"
RECEIPT = Path(__file__).resolve().parents[2] / "data" / "refresh-receipt.json"

# Figure ids a claim may name that are not sources (their numbers live inline in a page for now).
# `known` for evaluate() is exactly: source ids | this. Anything else a claim names is a typo and raises.
NON_SOURCE_FIGURES = frozenset({"ma_auto_expenditure", "us_auto_expenditure"})


@dataclass
class Move:
    source_id: str
    held: str
    newest: str
    is_final: bool
    evidence_url: str


@dataclass
class Failure:
    source_id: str
    error: str


@dataclass
class Skipped:
    """A human_fetch source the survey did not probe; Task 6 ages it by `due`."""
    source_id: str
    due: str | None
    held_period: str


@dataclass
class SurveyResult:
    """Deliberately not a container: no len, bool, iter or index.

    A survey with zero moves and a failure is not "all clear", so every consumer
    must write `.moves`, `.failures` or `.skipped` on purpose.
    """
    moves: list[Move]
    failures: list[Failure]
    skipped: list[Skipped]


def survey(sources: list[Source], *, fetch=urlopen_text) -> SurveyResult:
    out = SurveyResult([], [], [])
    for s in sources:
        if s.human_fetch:  # publisher blocks automated clients; ages by `due` alone
            out.skipped.append(Skipped(s.id, s.due, s.held_period))
            continue
        try:
            p = probe(s, fetch=fetch)
        except ProbeError as e:
            out.failures.append(Failure(s.id, str(e)))
            continue
        if p.newest_period != s.held_period:
            out.moves.append(Move(s.id, s.held_period, p.newest_period, p.is_final, p.evidence_url))
    return out


# --- apply: the first code here that writes published files ---------------------------------

ROOT = Path(__file__).resolve().parents[2]

# Census NAME -> postal code: the 50 states + DC. A complete response must name all 51.
STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


class FetchError(Exception):
    """The publisher's answer was missing, short or unreadable. Nothing was written."""


class Conflict(Exception):
    """Another session changed what this apply was based on. Do not commit."""


@dataclass
class Applied:
    source_id: str
    old: dict
    new: dict
    files_written: list[str]
    divergences: list[str]  # targets that still disagree with `new` after the write; [] is healthy


def _source_label(year):
    return f"Census ACS 1-Year {year} (B19113 family, B19013 household)"


def _num(x, what):
    """Positive finite float from a Census cell. Census uses null / negative sentinels for suppressed."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise FetchError(f"{what}: not a number ({x!r})") from None
    if not v > 0 or v == float("inf"):
        raise FetchError(f"{what}: not a usable figure ({x!r})")
    return v


def _get_rows(fetch, url, shown, key):
    try:
        rows = json.loads(fetch(url))
        head, body = rows[0], rows[1:]
        if not isinstance(head, list) or not all(isinstance(r, list) for r in body):
            raise ValueError("not a table")
    except Exception as e:  # unreachable, 404, bad JSON, wrong shape: all untrustworthy
        # urlopen_text raises NotFound(url) with the KEYED url, and a traceback prints the chained
        # cause too: scrub the key from the text and cut the chain (`from None`). Task 7 prints
        # failures into a CI log.
        raise FetchError(f"{shown}: {type(e).__name__}: {e}".replace(key, "***")) from None
    return head, body


def _fetch_acs(year, fetch, key):
    """Everything validated in memory; raises FetchError before anything touches disk."""
    base = f"https://api.census.gov/data/{year}/acs/acs1?get="
    tail = f"&key={key}"
    shown = lambda q: base + q  # the key never reaches an error message or a file
    q = "NAME,B19113_001E,B19013_001E&for=state:25"
    head, body = _get_rows(fetch, base + q + tail, shown(q), key)
    try:
        row = body[0]
        name, fam, hh = (row[head.index(c)] for c in ("NAME", "B19113_001E", "B19013_001E"))
    except (IndexError, ValueError) as e:
        raise FetchError(f"{shown(q)}: unreadable Massachusetts row ({e!r})") from e
    if name != "Massachusetts" or len(body) != 1:
        raise FetchError(f"{shown(q)}: not exactly the Massachusetts row ({name!r}, {len(body)} rows)")
    out = {"family": _num(fam, "B19113 family"), "household": _num(hh, "B19013 household")}

    q = "NAME,B19013_001E&for=state:*"
    head, body = _get_rows(fetch, base + q + tail, shown(q), key)
    try:
        ni, vi = head.index("NAME"), head.index("B19013_001E")
        got = {r[ni]: r[vi] for r in body}
    except (IndexError, ValueError) as e:
        raise FetchError(f"{shown(q)}: unreadable state table ({e!r})") from e
    missing = [n for n in STATES if n not in got]
    if missing:
        raise FetchError(f"{shown(q)}: short response, {len(STATES) - len(missing)} of "
                         f"{len(STATES)} states (missing {', '.join(missing[:5])}...)")
    by_state = {STATES[n]: _num(got[n], f"B19013 {n}") for n in STATES}
    if by_state["MA"] != out["household"]:
        raise FetchError(f"Massachusetts is {out['household']:.0f} in one call and "
                         f"{by_state['MA']:.0f} in the other: not one release")
    out["by_state"] = by_state

    q = "NAME,B19013_001E&for=us:1"
    head, body = _get_rows(fetch, base + q + tail, shown(q), key)
    try:
        out["us"] = _num(body[0][head.index("B19013_001E")], "B19013 US")
    except (IndexError, ValueError) as e:
        raise FetchError(f"{shown(q)}: unreadable US row ({e!r})") from e
    out["by_state_url"] = base + "NAME,B19013_001E&for=state:*"
    out["ma_url"] = base + "NAME,B19013_001E&for=state:25"
    return out


# Each target kind: read(text) -> what it holds; edit(text, f, year, today) -> new text (same
# text back if it already holds f). Both see raw text read with newline='', so bytes survive.

_COL = re.compile(r'(<script id="col-data" type="application/json">)(.*?)(</script>)', re.S)


def _html_income(text):
    m = _COL.search(text)
    if not m or m.group(2).count('"income":') != 1:
        raise ValueError("affordability-dashboard.html: need exactly one col-data block with one income object")
    a = m.start(2) + m.group(2).index('"income":') + len('"income":')
    old, end = json.JSONDecoder().raw_decode(text, a)
    if json.dumps(old, separators=(",", ":")) != text[a:end]:
        raise ValueError("affordability-dashboard.html: income object is not in the compact form apply writes")
    return a, end, old


def _html_read(text):
    inc = _html_income(text)[2]
    return {"household": inc["household"], "family": inc["family"], "vintage": inc["vintage"],
            "source": inc["source"], "ma_in_map": inc["household_by_state"]["MA"]}


def _new_income(old, f, year, today):
    """The `.income` object both the HTML blob and cost-of-living-latest.json carry: same shape,
    same key order. Returns `old` itself when it already holds f (so dates are not restamped)."""
    if "household_by_state" not in old:
        raise ValueError("income object has no household_by_state to refresh")
    new = {
        "household": f["household"], "family": f["family"], "vintage": year,
        "source": _source_label(year),
        # same 50 keys the page already holds; DC is fetched to prove the map is whole, not published
        "household_by_state": {ab: f["by_state"][ab] for ab in old["household_by_state"]},
        "household_us": f["us"],
        "household_by_state_url": f["by_state_url"],
        "household_by_state_retrieved": old.get("household_by_state_retrieved"),
    }
    if new == old:
        return old
    new["household_by_state_retrieved"] = today
    return new


def _html_edit(text, f, year, today):
    a, end, old = _html_income(text)
    new = _new_income(old, f, year, today)
    if new is old:
        return text
    return text[:a] + json.dumps(new, separators=(",", ":")) + text[end:]


def _eol(text):
    crlf = text.count("\r\n")
    if crlf and text.count("\n") != crlf:
        raise ValueError("mixed line endings: refusing to rewrite")
    return "\r\n" if crlf else "\n"


def _json_dump(data, eol, indent=2, ascii_=False, nl="\n"):
    return (json.dumps(data, indent=indent, ensure_ascii=ascii_) + nl).replace("\n", eol)


def _col_load(text):
    """data/cost-of-living-latest.json: indent=1, ASCII, no trailing newline (update-cost-of-living.py)."""
    data, eol = json.loads(text), _eol(text)
    if _json_dump(data, eol, 1, True, "") != text:
        raise ValueError("cost-of-living-latest.json: re-serialising it would change formatting")
    return data, eol


def _col_read(text):
    inc = json.loads(text)["income"]
    return {"household": inc["household"], "family": inc["family"], "vintage": inc["vintage"],
            "source": inc["source"], "ma_in_map": inc["household_by_state"]["MA"]}


def _col_edit(text, f, year, today):
    data, eol = _col_load(text)
    new = _new_income(data["income"], f, year, today)
    if new is data["income"]:
        return text
    data["income"] = new
    return _json_dump(data, eol, 1, True, "")


def _burden_node(data):
    try:
        return data["states"]["MA"]["acs"]["medianHouseholdIncome_ACS"]
    except KeyError as e:
        raise ValueError(f"burden-constants.json: no states.MA.acs.medianHouseholdIncome_ACS ({e})") from e


def _burden_read(text):
    return {"household": float(_burden_node(json.loads(text))["value"])}


def _burden_edit(text, f, year, today):
    data, eol = json.loads(text), _eol(text)
    if _json_dump(data, eol) != text:  # a whole-file rewrite must not reformat anything
        raise ValueError("burden-constants.json: re-serialising it would change formatting")
    node = _burden_node(data)
    hh = int(f["household"]) if f["household"].is_integer() else f["household"]
    stamp = {"value": hh, "source": f"Census ACS {year} 1-year, Table B19013 (Census API, direct)",
             "url": f["ma_url"]}
    if all(node.get(k) == v for k, v in stamp.items()):
        return text
    node.update(stamp)
    node["verified"] = today
    return _json_dump(data, eol)


_KINDS = {"affordability-dashboard.html": (_html_read, _html_edit),
          "data/burden-constants.json": (_burden_read, _burden_edit),
          "data/cost-of-living-latest.json": (_col_read, _col_edit)}


def _write_text(path, text):
    """Replace path with text byte-for-byte (no newline translation), atomically."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    os.replace(tmp, path)


def _read_text(path):
    return path.read_bytes().decode("utf-8")


def _divergent(root, targets, new):
    out = []
    for t in targets:
        for k, v in _KINDS[t][0](_read_text(root / t)).items():
            if v != (new["household"] if k == "ma_in_map" else new[k]):
                out.append(t)
                break
    return out


def apply(move: Move, *, fetch=urlopen_text, dry=False, root: Path = ROOT, today: str | None = None) -> Applied:
    """Fetch the move's ACS release, validate it whole, then write every target. ACS only.

    Nothing is written until the complete new value is built and every target's new text
    exists in memory. A write that fails partway restores the files already written.
    """
    today = today or datetime.date.today().isoformat()
    src = {s.id: s for s in load_sources(root / "data" / "sources.json")}.get(move.source_id)
    if src is None or src.probe != "census_acs1":
        raise ValueError(f"{move.source_id}: apply handles census_acs1 sources only")
    absent = [t for t in _KINDS if t not in src.targets]
    if absent:  # all three hold one figure; a register missing one would let it go stale
        raise ValueError(f"{move.source_id}: register is missing required target(s) {absent}")
    unknown = [t for t in src.targets if t not in _KINDS]
    if unknown:
        raise ValueError(f"{move.source_id}: no writer for target(s) {unknown}")
    if not move.newest.isdigit():
        raise ValueError(f"{move.source_id}: newest period {move.newest!r} is not a year")
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        raise FetchError("CENSUS_API_KEY is not set: the Census API refuses keyless requests")
    year = int(move.newest)

    f = _fetch_acs(year, fetch, key)  # raises FetchError: nothing below has run

    olds = {t: _read_text(root / t) for t in src.targets}
    news = {t: _KINDS[t][1](olds[t], f, year, today) for t in src.targets}  # may raise ValueError
    inc = _html_income(olds["affordability-dashboard.html"])[2]
    view = lambda d: {k: d[k] for k in ("household", "family", "vintage", "source")}
    new_view = view({"household": f["household"], "family": f["family"], "vintage": year,
                     "source": _source_label(year)})

    changed = [t for t in src.targets if news[t] != olds[t]]
    written = []
    if not dry:
        try:
            for t in changed:
                _write_text(root / t, news[t])
                written.append(t)
        except Exception:
            # ponytail: if a restore itself fails, that error replaces the original one and the
            # file is left half-restored; acceptable for a local disk, add chaining if it ever bites.
            for t in written:
                _write_text(root / t, olds[t])
            raise
    return Applied(move.source_id, view(inc), new_view, written, _divergent(root, src.targets, new_view))


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def pull_and_recheck(applied: Applied, move: Move, *, fetch=urlopen_text, root: Path = ROOT, git=_git) -> list[str]:
    """Run before committing: pull the other sessions' work, then prove the move still stands.

    Raises Conflict if the pull fails, if the register's held period changed underneath
    (someone applied or bumped it), or if a fresh survey no longer reports this move.
    Returns the targets that still disagree after the pull ([] is healthy).
    """
    try:
        git(["pull", "--rebase", "--autostash"], root)
    except Exception as e:
        raise Conflict(f"git pull --rebase failed: {e}") from e
    src = {s.id: s for s in load_sources(root / "data" / "sources.json")}.get(move.source_id)
    if src is None or src.held_period != move.held:
        raise Conflict(f"{move.source_id}: held period is now "
                       f"{src.held_period if src else 'absent'}, was {move.held}")
    r = survey([src], fetch=fetch)
    if r.failures:
        raise Conflict(f"{move.source_id}: cannot re-verify: {r.failures[0].error}")
    if not any(m.newest == move.newest for m in r.moves):
        raise Conflict(f"{move.source_id}: the survey no longer reports {move.held} -> {move.newest}")
    return _divergent(root, src.targets, applied.new)


def apply_and_recheck(m: Move, *, apply_fn=apply, recheck=pull_and_recheck, git=_git, root: Path = ROOT) -> Applied:
    """What main passes to run(): apply, then pull and re-verify BEFORE anything is committed.

    Two sessions work this repo at once, so the tree we just wrote may sit on stale main.
    On any doubt the written files go back to HEAD and Conflict is raised, which run() records
    as unresolved: the gate fails and the receipt says why, rather than a wrong figure being pushed.
    """
    a = apply_fn(m)
    if not a.files_written:
        return a  # nothing on disk to protect
    try:
        left = recheck(a, m)
        if left:
            raise Conflict(f"{m.source_id}: after pulling, {left} still disagree with the new figure")
    except Exception as e:
        try:
            git(["checkout", "HEAD", "--", *a.files_written], root)
        except Exception:
            pass  # the original problem is the one to report
        if isinstance(e, Conflict):
            raise
        raise Conflict(f"{m.source_id}: {type(e).__name__}: {e}") from None
    return a


def run(sources: list[Source], claims, *, fetch=urlopen_text, apply_fn=apply, today: str | None = None) -> RunRecord:
    """One complete run: survey, apply what we may, judge the claims. Writes nothing itself
    (apply_fn does, for apply:true sources). Only plain strings are kept from any failure:
    `str(e)` of the scrubbed FetchError, never the exception, never its chain."""
    today = today or datetime.date.today().isoformat()
    by_id = {s.id: s for s in sources}
    result = survey(sources, fetch=fetch)
    rec = RunRecord(run_date=today, claims=claims)
    for m in result.moves:
        if not by_id[m.source_id].apply:
            rec.deferred.append(m)  # moved, plan says not this pass: report it, do not fail the gate
            continue
        try:
            rec.applied.append(apply_fn(m))
        except (FetchError, ValueError, OSError, Conflict) as e:
            rec.unresolved.append(Failure(m.source_id, f"{type(e).__name__}: {e}"))
    for f in result.failures:
        # cannot tell whether it moved: gate-failing for a source we would write, reported for one we would not
        (rec.unresolved if by_id[f.source_id].apply else rec.probe_failures).append(f)
    # a human_fetch source is never probed, so its due date is the only thing ageing it
    rec.overdue = [k for k in result.skipped if k.due is None or k.due < today]

    moved = {m.source_id for m in result.moves}
    known = {s.id for s in sources} | NON_SOURCE_FIGURES
    moved_claims = {c.id for c in claims if moved & set(c.figures)}
    # No figure values are supplied yet (the auto numbers are inline chart arrays), so relation claims
    # come back "suspect" every run. Keep a suspect only when a figure under it moved this run;
    # otherwise it would be noise, and noise is what teaches the reader to ignore the flag.
    rec.verdicts = [v for v in evaluate(claims, {}, moved=moved, known=known)
                    if v.status == "broken" or (v.status == "suspect" and v.claim_id in moved_claims)]
    return rec


def main(argv=None, *, fetch=urlopen_text) -> int:
    ap = argparse.ArgumentParser(description="Survey publishers for newer editions.")
    ap.add_argument("--dry-run", action="store_true", help="survey and print; write nothing, send no receipt")
    ap.add_argument("--register", type=Path, default=REGISTER)
    ap.add_argument("--claims", type=Path, default=CLAIMS)
    ap.add_argument("--receipt", type=Path, default=RECEIPT)
    args = ap.parse_args(argv)
    sources = load_sources(args.register)
    if not args.dry_run:
        rec = run(sources, load_claims(args.claims), fetch=fetch, apply_fn=apply_and_recheck)
        write_receipt(args.receipt, rec)  # last: it records a COMPLETED run, which is what the gate trusts
        msg = format_message(rec)
        if msg:
            print(msg)
        return 0  # the verdict is the receipt + check-freshness.py, not this exit code
    result = survey(sources, fetch=fetch)
    moved = {m.source_id: m for m in result.moves}
    skipped = {k.source_id for k in result.skipped}
    failed = {f.source_id: f for f in result.failures}
    for s in sources:
        if s.id in skipped:
            due = f", due {s.due}" if s.due else ""
            print(f"{s.id}: skipped, fetched by hand{due} (holds {s.held_period})")
        elif s.id in failed:
            print(f"{s.id}: FAILED to probe: {failed[s.id].error}")
        elif s.id in moved:
            m = moved[s.id]
            stage = "final" if m.is_final else "stage one, not final"
            print(f"{s.id}: MOVED {m.held} -> {m.newest} ({stage}) {m.evidence_url}")
        else:
            print(f"{s.id}: no move (holds {s.held_period})")
    return 1 if result.failures else 0


if __name__ == "__main__":
    sys.exit(main())
