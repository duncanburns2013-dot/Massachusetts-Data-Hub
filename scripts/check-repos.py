#!/usr/bin/env python3
"""Fail when another repo's automation has stopped working.

WHY THIS EXISTS
check-freshness.py asks "is this file old?" and check-consistency.py asks "does
the page agree with the feed?" -- both only about THIS repo. Nothing asked the
question one level up: is the job that writes the feed still running at all?

The Peoples Audit has nine scheduled workflows and no health check of any kind.
If fetch-cthru-aggregates or fetch-state-contracts started failing, nothing would
say so until someone opened the Actions tab. That is the same silent-stop this
repo has learned about the hard way, just in a repo that cannot see itself.

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


class RateLimited(Exception):
    """The API refused us; nothing was learned about this repo."""


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
            # Was `raise SystemExit(0)`: a rate-limited pass printed one line
            # and exited GREEN, so "Every watched repo's automation is
            # running" was reported on a pass that had verified nothing. This
            # watchdog exists because a stopped feed is silent; it must not
            # become silent itself. Raised now and counted as unverified.
            raise RateLimited("rate-limited by the GitHub API")
        raise


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
    unverified = []
    for repo in REPOS:
        print(f"{repo} ...")
        try:
            found = check(repo)
        except RateLimited as e:
            print(f"  {e} - nothing verified for this repo")
            unverified.append(repo)
            continue
        except urllib.error.HTTPError as e:
            print(f"  cannot read ({e.code}) - nothing verified for this repo")
            unverified.append(repo)
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
    # The claim this job makes on a green run is "every watched repo's
    # automation is running". It may only make that claim about repos it could
    # actually read. Until 2026-11-22 a 403 raised SystemExit(0) from inside
    # api(), so a wholly rate-limited pass printed one line and exited green,
    # making the claim about nothing.
    #
    # Failing on ANY unverified repo was my first fix and it is too brittle:
    # this file's own header says a failure here is "worth an email", and a
    # transient rate limit is not the same event as a stopped cron. So the
    # claim is narrowed to what was read, the gap is printed where a reader
    # will see it, and the run only FAILS when nothing at all was verified --
    # which means the watchdog is giving no signal and that is worth an email.
    checked = [r for r in REPOS if r not in unverified]
    if unverified:
        print("\nNOT VERIFIED: %d of %d repo(s) could not be read (%s)."
              % (len(unverified), len(REPOS), ", ".join(unverified)),
              file=sys.stderr)
        print("No claim is made about their automation. Re-run with a token, "
              "or wait out the rate limit.", file=sys.stderr)
    if not checked:
        print("\nNOTHING was verified, so this watchdog reported nothing "
              "at all.", file=sys.stderr)
        return 1

    print("\nAutomation is running in all %d repo(s) this pass could read."
          % len(checked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
