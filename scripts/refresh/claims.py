"""The claim registry: sentences on the site that rest on a figure, and whether they still hold."""
import json
import math
import re
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import Path


class UnknownFigure(Exception):
    """A claim names a figure id that exists nowhere. Never skipped: a typo'd id would
    leave a public sentence the system believes it is watching and is not."""


@dataclass
class Claim:
    id: str
    page: str = ""
    text: str = ""
    figures: list[str] = field(default_factory=list)
    relation: str | None = None
    anchor: str = ""  # literal snippet of the page that carries the claim, for the grounding test


@dataclass
class Verdict:
    claim_id: str
    status: str  # "holds" | "broken" | "suspect"


_ID = r"[A-Za-z_][A-Za-z0-9_]*"
_NUM = r"[0-9]+(?:\.[0-9]+)?(?:[eE][0-9]+)?"
_OPERAND = rf"(?:{_ID}|{_NUM})"
# two-character operators first so "<=" is not read as "<" then "="
_RELATION = re.compile(rf"\s*({_OPERAND})\s*(<=|>=|==|!=|<|>)\s*({_OPERAND})\s*", re.ASCII)
_OPS = {
    "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
}
_REQUIRED = ("id", "page", "text", "figures")


def load_claims(path: Path) -> list[Claim]:
    out = []
    for i, e in enumerate(json.loads(Path(path).read_text(encoding="utf-8"))):
        name = e.get("id", f"#{i}")
        missing = [k for k in _REQUIRED if k not in e]
        if missing:
            raise ValueError(f"claim {name}: missing {', '.join(missing)}")
        out.append(Claim(**{k: e[k] for k in _REQUIRED},
                         relation=e.get("relation"), anchor=e.get("anchor", "")))
    return out


def _parse(claim: Claim) -> tuple[str, str, str]:
    m = _RELATION.fullmatch(claim.relation)
    if not m:
        raise ValueError(f"claim {claim.id}: cannot parse relation {claim.relation!r}; "
                         "expected '<figure|number> <op> <figure|number>', "
                         "op one of < <= > >= == !=")
    return m.group(1), m.group(2), m.group(3)


def _is_number(tok: str) -> bool:
    return re.fullmatch(_NUM, tok) is not None


def evaluate(claims: list[Claim], figures: dict[str, float],
             moved: Collection[str] = frozenset(),
             known: Collection[str] | None = None) -> list[Verdict]:
    """One Verdict per claim, in order.

    An id is *known* if it is a key of `figures` or in `known` (ids that exist in the system
    but have no value this run). An id that is neither raises UnknownFigure. A claim that
    needs a value it was not handed (known, no value) is "suspect": we cannot check it, and
    we do not say it holds.
    """
    if isinstance(moved, (str, bytes)):
        raise TypeError("moved must be a collection of figure ids, not a bare string")
    exists = set(figures) | set(known or ())
    stray = sorted(set(moved) - exists)
    if stray:
        raise UnknownFigure(f"moved names unregistered figure(s): {', '.join(stray)}")
    out = []
    for c in claims:
        parsed = _parse(c) if c.relation is not None else None
        ids = list(c.figures)
        if parsed:
            ids += [t for t in (parsed[0], parsed[2]) if not _is_number(t)]
        unknown = sorted({f for f in ids if f not in exists})
        if unknown:
            raise UnknownFigure(f"claim {c.id} names unregistered figure(s): {', '.join(unknown)}")
        if parsed is None:
            out.append(Verdict(c.id, "suspect" if any(f in moved for f in c.figures) else "holds"))
            continue
        lhs, op, rhs = parsed
        if any(t not in figures for t in (lhs, rhs) if not _is_number(t)):
            out.append(Verdict(c.id, "suspect"))
            continue
        a, b = (_value(t, figures, c) for t in (lhs, rhs))
        out.append(Verdict(c.id, "holds" if _OPS[op](a, b) else "broken"))
    return out


def _value(tok: str, figures: dict[str, float], claim: Claim) -> float:
    v = float(tok) if _is_number(tok) else figures[tok]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"claim {claim.id}: figure {tok!r} is not a finite number: {v!r}")
    return v
