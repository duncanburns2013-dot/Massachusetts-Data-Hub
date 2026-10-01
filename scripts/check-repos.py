#!/usr/bin/env python3
"""Fail when another repo's automation has stopped working.

WHY THIS EXISTS
check-freshness.py asks "is this file old?" and check-consistency.py asks "does
the page agree with the feed?" -- both only about THIS repo. Nothing asked the
question one level up: is the job that writes the feed still running at all?

The Peoples Audit has nine scheduled workflows and no health check of any kind.
If fetch-cthru-aggregates or fetch-state-contracts started failing, nothing would
say so until someone opened the Actions tab. That is the same silent-stop this
repo已 learned about the hard way, just in a repo that cannot see itself.

Two failure modes, both silent:

  FAILING   the newest run of a scheduled workflow is red, and no run has
            succeeded since. One red run is not an alert -- feeds have bad days
            and most of these jobs retry. A red run with no success behind it is.

  STOPPED   the workflow has not run in far longer than its cron implies.
            GitHub DISABLES scheduled workflows in repositories with no pushes
            for 60 days, silently, and that is exactly the kind of thing nobody
            notices until the data is a season old.

Read-only, unauthenticated: every repo here is public, and one pass costs about
a dozen API calls against a 60/hour anonymous budget. GITHUB_TOKEN is used when
present purely for the higher rate limit.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

OWNER = "duncanburns2013-dot"

# Repos whose automation actually matters. A repo with no scheduled workflow is
# skipped automatically, so adding one here is harmless.
REPOS = [
    "Massachusetts-Data-Hub",
    "The-Peoples-Audit",
    "All-Things-Boston",
    "MA-Housing-Dashboard",
    "HHS-MA-DOGE",
]

# Workflows that are expected to be quiet. A name here is never reported STOPPED.
EXPECT_QUIET = {
    # fires only on workflow_dispatch / push; the cron line is commented out
    "fetch-ma-sfi.yml",
    "publish-sfi-pdfs.yml",
    "fix-dates.yml",
    "reextract-sfi.yml",
}

NOW = datetime.datetime.now(datetime.timezone.utc)


def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "ma-data-hub-repo-watchdog"},
    )
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("  rate-limited by the API; skipping the rest of this pass")
            raise SystemExit(0)
        raise


def cron_days(expr):
    """Roughly how many days between firings. Generous on purpose."""
    f = expr.split()
    if len(f) != 5:
        return 7
    dom, mon, dow = f[2], f[3], f[4]
    if dom != "*" and dom.isdigit():
        return 31              # monthly
    if dow != "*":
        return 7 / max(1, len(dow.split(",")))
    if f[1].startswith("*/"):
        try:
            return int(f[1][2:]) / 24
        except ValueError:
            return 1
    return 1                   # daily


def check(repo):
    out = []
    wfs = api(f"/repos/{OWNER}/{repo}/actions/workflows").get("workflows", [])
    for wf in wfs:
        name = wf["path"].split("/")[-1]
        if wf["path"].startswith("dynamic/"):
            continue              # GitHub-managed (pages-build-deployment etc.)
        if wf.get("state") != "active":
            if wf.get("state") == "disabled_inactivity":
                out.append((repo, name, "DISABLED",
                            "GitHub disabled it for repository inactivity"))
            continue
        runs = api(f"/repos/{OWNER}/{repo}/actions/workflows/{wf['id']}"
                   f"/runs?per_page=30").get("workflow_runs", [])
        if not runs:
            continue
        newest = runs[0]
        if newest["conclusion"] == "failure":
            # one bad day is not an alert; a red run with no success behind it is
            if (any(r["event"] == "schedule" for r in runs)
                    and not any(r["conclusion"] == "success" for r in runs[:5])):
                out.append((repo, name, "FAILING",
                            f"last {min(5, len(runs))} runs, none succeeded"))
            continue

        # scheduled and gone quiet?
        if name in EXPECT_QUIET:
            continue
        if not any(r["event"] == "schedule" for r in runs):
            continue                      # manual-only; silence is correct
        last = datetime.datetime.fromisoformat(
            newest["created_at"].replace("Z", "+00:00"))
        age = (NOW - last).days

        # The cron is not in the API response, so the budget is inferred from
        # observed spacing -- and it must be the LARGEST gap, not the typical one.
        # Several of these schedules fire in bursts: update-cpi.yml is
        # "0 14 10-16 * *", seven consecutive days then twenty-three silent ones.
        # Taking the median gap sees the 1-day spacing inside the burst, calls it
        # a daily job, and reports a perfectly healthy workflow as STOPPED four
        # days into its normal quiet stretch. Both it and update-employment.yml
        # were reported that way on the first run of this script.
        stamps = [datetime.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                  for r in runs if r["event"] == "schedule"]
        gaps = [(stamps[i] - stamps[i + 1]).total_seconds() / 86400
                for i in range(len(stamps) - 1)]
        if len(gaps) < 2:
            continue                      # not enough history to judge
        widest = max(gaps)
        budget = max(5, widest * 2.5)
        if age > budget:
            out.append((repo, name, "STOPPED",
                        f"{age}d since last run; widest normal gap {widest:.0f}d"))
    return out


def main():
    problems = []
    for repo in REPOS:
        print(f"{repo} ...")
        try:
            found = check(repo)
        except urllib.error.HTTPError as e:
            print(f"  cannot read ({e.code}) - skipped")
            continue
        for p in found:
            print(f"  {p[2]:9s} {p[1]:34s} {p[3]}")
        if not found:
            print("  all scheduled workflows healthy")
        problems += found

    if problems:
        print(f"\n{len(problems)} workflow(s) in trouble:\n")
        for repo, name, kind, why in problems:
            print(f"  {kind:9s} {repo}/{name}")
            print(f"            {why}")
            print(f"            https://github.com/{OWNER}/{repo}/actions/workflows/{name}")
        print("\nA STOPPED workflow in a quiet repo is usually GitHub disabling the")
        print("schedule after 60 days without a push; re-enable it from the Actions tab.")
        return 1

    print("\nEvery watched repo's automation is running.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
