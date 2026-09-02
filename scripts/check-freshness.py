#!/usr/bin/env python3
"""Fail when any published figure has gone stale.

WHY THIS EXISTS
A feed that BREAKS is loud: the workflow goes red and mails you. A feed that
quietly stops updating is silent, and silence is the failure mode that actually
bit. update-cbp exits 75 and reports a neutral skip when cbp.gov blocks it --
deliberately, so a transient block does not mail a failure -- but that also means
the immigration page can age for weeks with every workflow green. It did: found
at 18 days stale only because someone happened to look at the page.

So: freshness is checked as its own thing, on its own schedule, and it is the one
job allowed to be noisy. Everything here is a number already published on the
site, so an alert means readers are looking at something older than it claims.

MAX AGES are set from each feed's OWN observed history (median and worst gap
between real updates, measured over its last ~14 commits) with roughly 2x
headroom, so a normal slow week is not an alert and a stopped feed is.
"""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TODAY = datetime.date.today()

# path, max age in days, why that number
DATA = [
    ("data/nh-figures.json",              7,  "daily pull; worst real gap 3d"),
    ("data/nh-state-monthly.json",        7,  "daily pull; worst real gap 3d"),
    ("data/housing-history-latest.json",  5,  "daily pull; worst real gap 1d"),
    ("data/price-distribution-latest.json", 5, "daily pull; worst real gap 1d"),
    ("data/employment-latest.json",      21,  "tracks BLS releases; worst real gap 7d"),
    ("data/cost-of-living-latest.json",  45,  "monthly BEA/MIT; worst real gap 13d"),
    # Polled daily by the self-hosted runner, but only committed when CBP
    # actually publishes -- the updater keeps the old fetched_at on a no-op run
    # precisely so this check keeps measuring the data and not the heartbeat.
    ("data/cbp-encounters-latest.json",  60,  "monthly source; runner polls daily"),
    ("data/census-latest.json",          75,  "monthly job, annual source; worst gap 26d"),
    ("data/irs-soi-migration-latest.json", 75, "monthly job, annual source; worst gap 31d"),
]

# Figures whose freshness lives in the page, not in a data file.
STAMPS = [
    ("ma-housing-dashboard.html", r"DATA_ASOF\s*=\s*'([^']+)'", "%B %d, %Y", 5,
     "MLS tail is refetched nightly"),
    ("energy-dashboard.html", r"FUEL_NOW = \{asOf:'([^']+)'", "%Y-%m-%d", 45,
     "EIA weekly retail prices, monthly job"),
]

# Deliberately NOT checked, so the list is a decision rather than an oversight:
#   mls-history.json          written only by --backfill-history
#   employment-previous.json  a kept snapshot; ageing is the point
#   burden-constants.json, payments.json, bls-release-schedule.json,
#   national-payroll-vintages.json   hand-curated or single-write


def last_changed(rel: str):
    out = subprocess.run(
        ["git", "log", "-1", "--format=%ad", "--date=short", "--", rel],
        cwd=REPO, capture_output=True, text=True).stdout.strip()
    return datetime.date.fromisoformat(out) if out else None


def main() -> int:
    rows, stale = [], []

    for rel, max_age, why in DATA:
        p = REPO / rel
        if not p.exists():
            stale.append((rel, "MISSING", max_age, why))
            rows.append((rel, "missing", max_age, "MISSING"))
            continue
        d = last_changed(rel)
        if d is None:
            rows.append((rel, "untracked", max_age, "skip"))
            continue
        age = (TODAY - d).days
        bad = age > max_age
        rows.append((rel, f"{age}d", max_age, "STALE" if bad else "ok"))
        if bad:
            stale.append((rel, f"{age} days old (last change {d})", max_age, why))

    for rel, pat, fmt, max_age, why in STAMPS:
        p = REPO / rel
        m = re.search(pat, p.read_text(encoding="utf-8")) if p.exists() else None
        if not m:
            stale.append((rel, "STAMP NOT FOUND", max_age, why))
            rows.append((rel, "no stamp", max_age, "STALE"))
            continue
        try:
            d = datetime.datetime.strptime(m.group(1).strip(), fmt).date()
        except ValueError:
            stale.append((rel, f"unparseable stamp {m.group(1)!r}", max_age, why))
            rows.append((rel, "unparseable", max_age, "STALE"))
            continue
        age = (TODAY - d).days
        bad = age > max_age
        rows.append((f"{rel} (stamp)", f"{age}d", max_age, "STALE" if bad else "ok"))
        if bad:
            stale.append((rel, f"page says {d}, {age} days ago", max_age, why))

    w = max(len(r[0]) for r in rows)
    print(f"{'source':<{w}}  {'age':>10}  {'limit':>6}  status")
    for name, age, lim, status in rows:
        print(f"{name:<{w}}  {age:>10}  {lim:>5}d  {status}")

    if not stale:
        print(f"\nAll {len(rows)} checked sources are current.")
        return 0

    print(f"\n{len(stale)} STALE:", file=sys.stderr)
    for rel, detail, max_age, why in stale:
        print(f"  {rel}: {detail} (limit {max_age}d — {why})", file=sys.stderr)
    print("\nA stale source means the site is publishing figures older than it "
          "implies. Re-run that feed's workflow. For CBP, check that the "
          "self-hosted runner is online -- cbp.gov 403s GitHub's IP ranges, so "
          "that feed can only come from duncanburns2013-dot/ma-data-hub-runner:\n"
          "  gh api repos/duncanburns2013-dot/ma-data-hub-runner/actions/runners"
          " --jq '.runners[].status'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
