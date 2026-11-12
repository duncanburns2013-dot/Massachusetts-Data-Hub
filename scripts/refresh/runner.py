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


class Survey(list):
    """The Moves found, plus `.failures` (publishers that could not be asked) and
    `.skipped` (human_fetch ids, never probed).

    A list subclass so `survey(...) == []` still reads as "no move". That alone is
    not "all clear": callers must also check `.failures`.
    """
    def __init__(self):
        super().__init__()
        self.failures: list[Failure] = []
        self.skipped: list[str] = []


def survey(sources: list[Source], *, fetch=urlopen_text) -> Survey:
    out = Survey()
    for s in sources:
        if s.human_fetch:  # publisher blocks automated clients; ages by `due` alone
            out.skipped.append(s.id)
            continue
        try:
            p = probe(s, fetch=fetch)
        except ProbeError as e:
            out.failures.append(Failure(s.id, str(e)))
            continue
        if p.newest_period != s.held_period:
            out.append(Move(s.id, s.held_period, p.newest_period, p.is_final, p.evidence_url))
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
    moved = {m.source_id: m for m in result}
    failed = {f.source_id: f for f in result.failures}
    for s in sources:
        if s.id in result.skipped:
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
