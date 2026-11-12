"""Reporting: the human-readable message, and the receipt the freshness gate reads.

Two channels. The message says what changed and what broke; it is None on a quiet run, because a
flag that fires every run teaches the reader to ignore flags. The receipt is the other half: it
proves the loop RAN, so that silence on the message channel can be trusted. check-freshness.py
fails when the receipt is missing or old.

Nothing here serialises an exception. Callers hand in already-scrubbed strings (`str(e)` of a
FetchError); the receipt holds ids and dates only.
"""
from __future__ import annotations

import datetime
import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunRecord:
    """What one completed run found. Types are runner.Applied / Failure / Move / Skipped and
    claims.Verdict; they are not imported so that runner can import this module."""
    applied: list = field(default_factory=list)
    verdicts: list = field(default_factory=list)       # already filtered by the caller; "holds" is ignored here
    unresolved: list = field(default_factory=list)     # Failure: apply:true source we could not resolve. Fails the gate.
    deferred: list = field(default_factory=list)       # Move: apply:false source that moved. Reported, never gating.
    overdue: list = field(default_factory=list)        # Skipped: human_fetch source past (or without) its due date
    probe_failures: list = field(default_factory=list)  # Failure: apply:false source we could not probe. Reported only.
    run_date: str = ""                                 # ISO date; "" means today


def _date(run: RunRecord) -> str:
    return run.run_date or datetime.date.today().isoformat()


def write_receipt(path: Path, run: RunRecord) -> None:
    """Record a completed run. Ids and dates only, so no secret can ride along."""
    path = Path(path)
    receipt = {
        "last_run": _date(run),
        "unresolved": [u.source_id for u in run.unresolved],
        "broken_claims": [v.claim_id for v in run.verdicts if v.status == "broken"],
        "deferred": [m.source_id for m in run.deferred],
        "overdue_human_fetch": [k.source_id for k in run.overdue],
        "probe_failures": [f.source_id for f in run.probe_failures],
    }
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _n(x) -> str:
    return f"{x:,.0f}" if isinstance(x, (int, float)) and float(x).is_integer() else f"{x:,}"


def format_message(run: RunRecord) -> str | None:
    """The report, or None when nothing moved and nothing broke."""
    broken = [v for v in run.verdicts if v.status == "broken"]
    suspect = [v for v in run.verdicts if v.status == "suspect"]
    if not (run.applied or broken or suspect or run.unresolved or run.deferred
            or run.overdue or run.probe_failures):
        return None
    out = [f"Data Hub refresh loop, {_date(run)}"]

    def section(title, lines):
        if lines:
            out.append("")
            out.append(title)
            out.extend(f"  {ln}" for ln in lines)

    section("BROKEN CLAIMS (a sentence on the site is now false; the gate fails)",
            [f"{v.claim_id}: broken" for v in broken])
    section("UNRESOLVED (publisher moved or could not be checked, nothing written; the gate fails)",
            [f"{u.source_id}: {u.error}" for u in run.unresolved])
    lines = []
    for a in run.applied:
        o, n = a.old, a.new
        lines.append(f"{a.source_id}: household {_n(o['household'])} -> {_n(n['household'])}, "
                     f"family {_n(o['family'])} -> {_n(n['family'])}, vintage {o['vintage']} -> {n['vintage']}")
        lines.append(f"  wrote: {', '.join(a.files_written) or 'nothing'}")
        if a.divergences:
            lines.append(f"  DIVERGED, still disagree after the write: {', '.join(a.divergences)}")
    section("APPLIED", lines)
    section("RE-READ (a figure moved under this sentence)", [f"{v.claim_id}" for v in suspect])
    section("DEFERRED (moved; not applied this pass, the gate does not fail)",
            [f"{m.source_id}: {m.held} -> {m.newest}" + ("" if m.is_final else " (stage one, not final)")
             for m in run.deferred])
    section("OVERDUE HUMAN FETCH (never probed; the due date is the only thing ageing it; the gate fails)",
            [f"{k.source_id}: " + (f"due {k.due}" if k.due else "no due date set") + f", holds {k.held_period}"
             for k in run.overdue])
    section("PROBE FAILURES (could not check; reported only)",
            [f"{f.source_id}: {f.error}" for f in run.probe_failures])
    text = "\n".join(out)
    key = os.environ.get("CENSUS_API_KEY")
    return text.replace(key, "***") if key else text
