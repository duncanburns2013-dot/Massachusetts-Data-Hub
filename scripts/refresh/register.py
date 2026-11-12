"""The source register: what the site holds and how to ask each publisher."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Source:
    id: str
    publisher: str
    probe: str
    held_period: str
    held_retrieved: str
    targets: list[str]
    multi_stage: bool
    final_tell: str | None
    human_fetch: bool
    due: str | None
    apply: bool


_REQUIRED = ("id", "publisher", "probe", "held_period", "held_retrieved",
             "targets", "multi_stage", "human_fetch", "apply")


def load_sources(path: Path) -> list[Source]:
    out = []
    for i, e in enumerate(json.loads(Path(path).read_text(encoding="utf-8"))):
        name = e.get("id", f"#{i}")
        missing = [k for k in _REQUIRED if k not in e]
        if missing:
            raise ValueError(f"source {name}: missing {', '.join(missing)}")
        out.append(Source(**{k: e[k] for k in _REQUIRED},
                          final_tell=e.get("final_tell"), due=e.get("due")))
    return out
