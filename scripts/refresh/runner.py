"""Runner: survey every source, report which publishers have moved. Writes nothing."""
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.refresh.probes import ProbeError, probe, urlopen_text
from scripts.refresh.register import Source, load_sources

REGISTER = Path(__file__).resolve().parents[2] / "data" / "sources.json"


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


def main(argv=None, *, fetch=urlopen_text) -> int:
    ap = argparse.ArgumentParser(description="Survey publishers for newer editions.")
    ap.add_argument("--dry-run", action="store_true", help="survey and print; write nothing")
    ap.add_argument("--register", type=Path, default=REGISTER)
    args = ap.parse_args(argv)
    if not args.dry_run:
        print("nothing to write yet: pass --dry-run", file=sys.stderr)
        return 2
    sources = load_sources(args.register)
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
