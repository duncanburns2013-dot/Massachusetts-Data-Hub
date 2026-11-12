# Data Hub refresh loop — design

**Date:** 2026-11-12
**For:** Duncan Burns
**Status:** design, approved to plan. Nothing here is built.

---

## Intent

The Data Hub goes stale and nobody is told. Today the only thing that reliably
surfaces a stale figure is Duncan asking Claude to check, and Claude finding
something wrong. Every automated check in the repo passed while it happened.

This describes a loop that notices a source has published something newer,
updates the data and charts by itself, publishes, and then tells Duncan which
written claims are now standing on numbers that moved.

### Why now

On 2026-11-12 a single afternoon's audit found four live errors on
massachusettsdatahub.com. All four were old. None was caught by the freshness
gate, the per-feed workflows, or the register. The common thread is not that
checks are missing — the repo has more checking machinery than most — it is
that **every check measures whether our own process ran, and none measures
whether the publisher has moved on.**

---

## The four failure modes, with evidence

These are the cases the design must defeat. All four are real and all four
were found on the same day.

### 1. Wrong-vintage fetch — automation runs green and fetches the wrong year

`update-cost-of-living.py` owns the income block on `affordability-dashboard.html`.
It ran on schedule, succeeded, and wrote a fresh `generated` timestamp every
time. It also keyed its ACS probe off `census-latest.json`'s `acs_vintage`,
which is the ACS **5-year** vintage, and only ever tried that year and 2023.
When ACS **1-year 2025** published on 2026-10-29, nothing asked for it. The page
sat on $104,828 (2024) with a green workflow and a current timestamp.

This is the worst mode, because every signal said healthy. A stamp check cannot
see it. A "did the workflow run" check cannot see it. Only comparing what we
hold against what the publisher currently offers can see it.

### 2. Superseded stage — the period is right, the record is not finished

MA DOI decides merged-market health rates in two stages. In July it announces
approvals and *rejects* some carriers; later each rejected carrier settles a
rate and the published table changes. The healthcare dashboard carried the July
2025 stage-one snapshot for CY2026, showing BCBS and WellSense as REJECTED.
They had in fact settled at 11.9% and 13.6% — and 13.6% was the highest approved
rate of that year, displayed on the site as a rejection.

`figure-gate`'s "newest published period" check passes here. The period was
correct. The *stage* was not. Cadence checking is not enough on its own.

### 3. Measure mismatch — two different measures compared as one

The auto section claimed MA is "7.8% BELOW the US average" from $1,326 against
$1,438. Those are different NAIC measures: $1,326.46 is MA average
**expenditure** 2023, $1,438.51 is countrywide average **premium** 2023. Like
for like, MA was 3.5% *above*. The page's single green "good news" card was
inverted, and had been for as long as the card existed.

No freshness mechanism can catch this; it is not a staleness bug. It is here
because the fix surfaced during the same audit and because the design's claim
registry (below) is the only part of this proposal that would have a hope of
flagging it.

### 4. Divergent copies — one figure, two files, two values

While `update-cost-of-living.py` held $104,828, `burden-constants.json` already
held $106,539 for the same figure. Two files in one repo, disagreeing, with
nothing comparing them.

---

## Goals

1. When a publisher releases something newer than what the Hub holds, the Hub
   finds out without anyone asking.
2. Data and charts update and publish automatically.
3. Written claims that rest on a figure that moved are flagged **to Duncan**,
   by message, naming the claim and what moved under it.
4. The same figure held in more than one place is reconciled, or the divergence
   is reported.

## Non-goals

- Rewriting prose automatically. See anti-goals.
- Covering all 23 pages in the first pass.
- Replacing the existing workflows, `check-freshness.py`, or `MASTER_DATA.md`.
  This extends them. Most of the machinery already exists and is good; what it
  lacks is the publisher-side question.
- Any reader-facing staleness indicator. Decided: the flag goes to Duncan only,
  nothing appears on the page.

## Anti-goals

Things that would make this a failure even if it technically worked:

- **A pipeline that edits a sentence.** `figure-gate` records that regexing
  prose to keep it current fails *silently* and has matched the wrong span
  twice. An automated narrative rewrite is the one component here that can put
  a false sentence on a public page with nobody in the loop. It is not built.
- **Another green checkmark.** The freshness gate has been emailing nothing
  because it passes. If this reports through a channel Duncan does not read, it
  has failed regardless of correctness.
- **A figure published without a primary source.** The loop writes only what it
  fetched from the publisher. If a fetch fails it reports and changes nothing.
  It never interpolates, never carries forward, never estimates.
- **Noise.** A flag that fires on every run teaches him to ignore flags.

---

## Constraints

- `F:\Massachusetts-Data-Hub` is canonical and publishes to
  massachusettsdatahub.com via GitHub Pages.
- Python, GitHub Actions, no new paid services. Existing stack only.
- Several sources actively block automated fetches: mass.gov pages (header
  filtering), CBP (Akamai client fingerprinting), the Secretary of the
  Commonwealth's lobbyist registry. Those stay human-fetched and must remain
  expressible in the register as "human reads this, here is when it is due."
- Some figures legitimately have no newer edition (CMS state health expenditures
  is on 2020 and that *is* the newest state edition). The design must be able to
  say "old on purpose, confirmed" without it reading as neglect.
- Two sessions sometimes work this repo at once. Anything automated must not
  clobber a hand edit, and must be safe to run while someone is mid-change.

---

## Design

Four parts. Each is an extension of something already in the repo.

### Part 1 — The source register

**Replaces date-guessing with publisher-asking.**

Today staleness is a *date arithmetic* question: `check-freshness.py` compares a
stamp to a limit, and `MASTER_DATA.md` carries `⏳ re-read by <date> — <why>`
rows that fail the build when overdue. That convention is good and stays. Its
weakness is that the date is a guess about the publisher's behaviour, which is
why affordability needed a hand-tuned 35-day limit to catch one known BEA
release.

Add, per figure or figure-group, a machine-readable record of:

- the publisher and the exact endpoint or document to check
- what we currently hold: value, period/vintage, and retrieval date
- **how to ask the publisher what its newest edition is** — a probe
- whether the record is multi-stage, and how to tell a provisional stage from a
  final one (the DOI case: carrier count is the tell — eight means final)
- whether a human must fetch it, and if so the due date (the existing `⏳` row)

The probe is the new idea and the important one. For ACS it is: walk back from
the current year requesting `acs/acs1` until one resolves — exactly what the
fixed `update-cost-of-living.py` now does, generalised. For BEA RPP it is: read
the release page for the newest data year. For NAIC it is: check for a newer
supplement edition.

**Where it lives** is left to the builder, with one requirement: it must be one
file per concern and diffable, so a vintage change shows up in `git diff` as a
line, not buried in a regenerated blob.

### Part 2 — The runner

On a schedule, for each registered figure:

1. Probe the publisher for its newest edition.
2. If it matches what we hold, record the check and stop. **This is the normal
   case and it must be silent.**
3. If newer, fetch it from the primary source. On any failure: change nothing,
   report, stop. Never partial-write.
4. Write the value, its period, its retrieval date and its source URL into the
   data file.
5. Reconcile: if the same figure appears elsewhere in the repo, update it too,
   or report the divergence (failure mode 4).
6. Charts need no step **on pages that hold their figures in a data blob**, and
   a great deal of work on pages that do not. This split is the main thing
   governing cost, and it is uneven:

   | Page | Inline numeric chart arrays |
   |---|---|
   | `affordability-dashboard.html` | 0 |
   | `tax-budget-dashboard.html` | 0 |
   | `healthcare-dashboard.html` | **41** |

   On affordability the ACS change of 2026-11-12 was four values in one JSON
   object and the on-screen "ACS 2025" label updated itself. On healthcare the
   same class of change meant hand-editing chart arrays, which is precisely why
   the 2026 rates sat wrong for a year: the figures live in the chart code, so
   nothing could own them.

   **So a page must be converted to a data blob before the loop can own it.**
   That conversion is a prerequisite per page, not a side effect, and it should
   be costed as such. `affordability-dashboard.html` is the reference shape.
7. Commit and publish.

### Part 3 — The claim registry

**The part that costs real effort, and the only part that makes "flag" possible.**

A written claim is a sentence on a page whose truth depends on a figure: "MA
auto is cheaper than the national average", "the median MA family earns less
than the living wage", "second straight double-digit year". Each gets registered
against the figures it rests on, and — where it can be expressed — the
*relationship* that makes it true: `ma_auto_expenditure < us_auto_expenditure`.

Then when a figure moves, the runner can say one of three things:

- the relationship still holds → claim is fine, say nothing
- the relationship broke → **flag, loudly**: this sentence is now false
- no relationship was recorded, only a dependency → **flag as suspect**: this
  sentence mentions a number that moved, read it

The inverted auto claim is the worked example. Registered as
`ma < us`, the mismatch would have been caught the first time the figures were
written, because the recorded relationship and the recorded values disagree.

This is per-claim work and it is Duncan's to do or to delegate. The honest
framing: it is the price of being flagged instead of being told nothing. It does
not need doing all at once — a claim with no registry entry simply behaves as
today, flagged as suspect whenever anything on its page moves.

### Part 4 — Reporting, on two channels

**Channel 1, the one that must work: a message to Duncan.** Not a log, not a
commit message. The scheduled-task mechanism already used for the BEA RPP
reminder posts into the Claude desktop app. One message per run that found
something, saying what moved, old and new, and which claims are now suspect or
broken. **A run that found nothing sends nothing.**

Silence therefore has to be trustworthy, which needs two things:

- **A probe that errors is a failure, not a pass.** If a publisher changes a URL
  or starts blocking us, the probe stops being able to answer "is there
  something newer" and must say so. Treating an unanswerable probe as "nothing
  new" rebuilds failure mode 1 inside the thing designed to prevent it.
- **A dead-man's switch.** If the loop itself stops running, silence looks
  exactly like all-clear. Record each successful run; if no run has completed
  inside its expected window, the gate fails. This is the same reasoning that
  put `check-freshness.py` in the repo in the first place — per its own
  docstring, a feed that breaks is loud, and a feed that quietly stops is the
  failure mode that actually bit.

**Channel 2, the backstop: the gate fails.** Duncan already receives GitHub
email when a workflow fails to run — that channel is proven. It has carried no
signal because the gate passes. So: when a probe finds a newer edition the loop
could not fetch, or a registered relationship breaks, `check-freshness.py`
**fails**. Stale stops looking like healthy.

---

## Decided

These are settled, by Duncan unless marked:

- Publish corrected data even when a headline above it is now wrong. Do not hold
  the page back. *(Duncan)*
- The flag goes to Duncan only. Nothing reader-facing. *(Duncan)*
- Primary channel is a message to him; GitHub email is the backstop. *(Duncan)*
- Narrative is never auto-rewritten. *(Claude's call, on the strength of
  `figure-gate`'s record that prose automation fails silently.)*
- First pass covers pages that already have a feed and a known cadence, not all
  23. *(Claude's call, stated and not objected to.)*
- Build on `check-freshness.py` and `MASTER_DATA.md` rather than beside them.
  *(Claude's call — the existing `⏳ re-read by` convention already proves the
  pattern that a forgotten row fails the build.)*

## Left to the builder

- Where the register and claim registry live, and in what format.
- How a probe is expressed — declarative config, or a small function per source.
  Per-source functions are likely, since BEA, Census, NAIC and DOI are
  genuinely different shapes.
- How reconciliation (step 5) identifies "the same figure" across files.
- Whether the runner commits directly or opens a PR. Duncan's "publish and flag"
  implies direct, but the builder should confirm this against the
  two-sessions-at-once constraint.
- Scheduling: one job for all sources, or per-source alongside the existing
  workflows.

## Suggested first pass

Start on `affordability-dashboard.html`. It is already the reference shape — no
inline chart arrays, figures in one data blob, a working ACS probe — so it
exercises the loop without also paying for a page conversion. `healthcare-dashboard.html`
should come later and be costed with its 41-array conversion included.

Three sources, chosen because each one exercises a different failure mode and
all three have already bitten:

1. **Census ACS 1-year** — failure mode 1. The probe already exists in fixed
   form; generalise it.
2. **BEA RPP** — releases 2026-12-10, which is a live test inside a month, and
   there is already a reminder scheduled for it.
3. **MA DOI merged-market rates** — failure mode 2, the multi-stage case, and
   the one that needs the "is this final?" tell.

Then one claim registered per page to prove Part 3 end to end before it is
rolled out widely.

---

## Open questions for Duncan

None blocking. The builder's questions above are theirs to settle.
