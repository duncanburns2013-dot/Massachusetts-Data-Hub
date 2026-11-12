# Data Hub Refresh Loop — First Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Hub notice when a publisher releases something newer than it holds, update `affordability-dashboard.html`'s data automatically, and tell Duncan which written claims now stand on numbers that moved.

**Architecture:** A small package under `scripts/refresh/`. A JSON register declares each figure's publisher, what we hold, and how to probe for a newer edition. Probes are one function per publisher, because BEA, Census and DOI are genuinely different shapes. A runner probes, fetches on a move, writes, reconciles duplicates and reports. Reporting lands on two channels: a message to Duncan, and `check-freshness.py` failing so GitHub's email carries the backstop.

**Tech Stack:** Python 3.12 stdlib only (`urllib`, `json`, `datetime`, `re`, `pathlib`). No new dependencies, no new paid services. GitHub Actions for scheduling.

**Spec:** `docs/superpowers/specs/2026-11-12-data-hub-refresh-loop-design.md`

## Global Constraints

- Python 3.12, **stdlib only**. No pip installs; this repo has no pytest and no `tests/` directory.
- Test convention is a standalone script under `scripts/` that prints and exits 0 on pass, 1 on fail — follow `scripts/test-mls-crosscheck.py`'s shape. Do not introduce pytest.
- Never write a figure not fetched from its publisher. On any fetch failure: report, change nothing, exit non-zero. No interpolation, no carry-forward, no estimates.
- Never partial-write a data file. Build the complete new value in memory, validate, then write once.
- Never rewrite prose. No task in this plan edits a sentence on a page.
- Nothing reader-facing. No staleness indicator renders on any page.
- `check-freshness.py` is CRLF; `affordability-dashboard.html` is LF. Preserve each file's existing line endings — open with `newline=''` and write back the same way.
- `CENSUS_API_KEY` resolves only in CI; the Census API refuses keyless requests. Local runs must degrade to a clear skip, never to a wrong number.
- Repo root on this machine is `F:\Massachusetts-Data-Hub`. Derive it from `Path(__file__).resolve().parents[2]`, never hardcode — `scripts/test-mls-crosscheck.py` hardcodes a path that does not exist here and cannot run as a result.

## Review Focus

Five conditions the spec implies that no task's happy path exercises. Each has its test pinned to the task that owns the code.

1. **A probe that cannot reach its publisher must fail, not report "nothing new."** A changed URL or a block would otherwise rebuild failure mode 1 inside the fix. — Task 2
2. **A fetch that returns fewer states than expected must abort the whole write.** The ACS state map covers 50 states + DC; a short response means a partial release or a truncated page, not a real move. — Task 4
3. **Two sessions commit to this repo at once.** A runner that commits onto a stale index will fail or clobber; it must pull-rebase and re-verify before pushing. — Task 4
4. **A claim naming a figure that is not in the register must fail loudly.** A typo'd figure id would otherwise make a claim permanently un-evaluable and permanently silent. — Task 5
5. **A loop that stops running must not look like a clean run.** Silence means all-clear, so absence of a recent run has to fail the gate. — Task 6

---

## File Structure

| File | Responsibility |
|---|---|
| `data/sources.json` | The register: one entry per figure — publisher, probe id, what we hold, where it lives |
| `data/claims.json` | The claim registry: sentence id, page, figures it rests on, optional relationship |
| `scripts/refresh/register.py` | Load and validate `sources.json`; the `Source` record |
| `scripts/refresh/probes.py` | One probe function per publisher; all return a newest-edition answer or raise |
| `scripts/refresh/claims.py` | Load `claims.json`, evaluate relationships against current figures |
| `scripts/refresh/runner.py` | Orchestrate: probe, fetch, write, reconcile, report. Entry point. |
| `scripts/refresh/report.py` | Format the message; write the run receipt the gate reads |
| `scripts/test-refresh-probes.py` | Probe tests, including unreachable-publisher |
| `scripts/test-refresh-runner.py` | Runner tests, including short-response abort |
| `scripts/test-refresh-claims.py` | Claim evaluation tests |
| `scripts/check-freshness.py` | Modified: read the run receipt, fail on stale receipt or unresolved move |

---

### Task 1: The source register

**Files:**
- Create: `data/sources.json`
- Create: `scripts/refresh/register.py`
- Test: `scripts/test-refresh-register.py`

**Interfaces:**
- Produces: `load_sources(path: Path) -> list[Source]`; `Source` is a dataclass with fields `id: str`, `publisher: str`, `probe: str`, `held_period: str`, `held_retrieved: str`, `targets: list[str]`, `multi_stage: bool`, `final_tell: str | None`, `human_fetch: bool`, `due: str | None`.
- `targets` are repo-relative paths of files holding this figure. More than one is legal and is what makes reconciliation possible.

- [ ] **Step 1: Write the failing test**

```python
# scripts/test-refresh-register.py
srcs = load_sources(REPO / "data" / "sources.json")
by_id = {s.id: s for s in srcs}
assert "census_acs1_ma_income" in by_id
acs = by_id["census_acs1_ma_income"]
assert acs.probe == "census_acs1"
assert acs.held_period == "2025"
assert "affordability-dashboard.html" in acs.targets
doi = by_id["doi_merged_market_rates"]
assert doi.multi_stage is True
assert doi.final_tell            # must say how to recognise a final stage
# a human-fetched source must carry a due date, or it ages by nothing
for s in srcs:
    if s.human_fetch:
        assert s.due, f"{s.id} is human-fetched with no due date"
# every target must exist
for s in srcs:
    for t in s.targets:
        assert (REPO / t).exists(), f"{s.id} -> missing target {t}"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python scripts/test-refresh-register.py`
Expected: FAIL — `scripts/refresh/register.py` does not exist.

- [ ] **Step 3: Write `data/sources.json` with three entries**

Seed exactly these, with values taken from the spec and from today's verified state:

| id | publisher | probe | held_period | targets |
|---|---|---|---|---|
| `census_acs1_ma_income` | Census ACS 1-year | `census_acs1` | `2025` | `affordability-dashboard.html`, `data/burden-constants.json` |
| `bea_rpp_state` | BEA Regional Price Parities | `bea_rpp` | `2024` | `affordability-dashboard.html`, `tax-budget-dashboard.html` |
| `doi_merged_market_rates` | MA DOI | `doi_rates` | `2027` | `healthcare-dashboard.html` |

`doi_merged_market_rates` gets `multi_stage: true` and `final_tell: "eight carriers in the Final Merged Market Rates table; fewer means the stage-one announcement"`. Confirm each `targets` path before writing it — the test asserts they exist.

- [ ] **Step 4: Implement `load_sources` in `scripts/refresh/register.py`**

Parse, build `Source` records, raise `ValueError` naming the entry on any missing required field.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python scripts/test-refresh-register.py` — Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add data/sources.json scripts/refresh/register.py scripts/test-refresh-register.py
git commit -m "refresh: source register, three seeded figures"
```

---

### Task 2: Probes

**Files:**
- Create: `scripts/refresh/probes.py`
- Test: `scripts/test-refresh-probes.py`

**Interfaces:**
- Consumes: `Source` from Task 1.
- Produces: `probe(source: Source, *, fetch=urlopen_text) -> Probe`, dispatching on `source.probe`. `Probe` is a dataclass: `newest_period: str`, `is_final: bool`, `evidence_url: str`.
- Raises `ProbeError` when it cannot determine an answer. **`ProbeError` is never caught as "nothing new"** — it propagates.
- `fetch` is injectable so tests never hit the network.

The three probes:
- `census_acs1` — walk back from the current year requesting `https://api.census.gov/data/{yr}/acs/acs1?get=NAME,B19113_001E,B19013_001E&for=state:25`; first year that resolves is newest. This generalises the loop now in `update-cost-of-living.py`, which is the fixed version of the bug that started all this.
- `bea_rpp` — read BEA's RPP product page for the newest data year.
- `doi_rates` — read `https://www.mass.gov/info-details/{yr}-health-insurance-rates`, count carrier rows in the Final table, set `is_final` per the register's `final_tell`. **Read the table, never the surrounding prose** — that page leaves stale "currently reviewing… final decision in August" copy sitting directly above a finished table.

- [ ] **Step 1: Write the failing tests**

```python
# scripts/test-refresh-probes.py
# newest edition found
p = probe(acs_source, fetch=stub_census({2025: OK, 2026: NOT_FOUND}))
assert p.newest_period == "2025"

# Review Focus 1 — an unreachable publisher must RAISE, never return "nothing new"
def boom(url): raise OSError("name resolution failed")
try:
    probe(acs_source, fetch=boom)
    assert False, "unreachable publisher reported a result"
except ProbeError:
    pass

# multi-stage: seven carriers is stage one, not final
p = probe(doi_source, fetch=stub_doi(carriers=7))
assert p.is_final is False
p = probe(doi_source, fetch=stub_doi(carriers=8))
assert p.is_final is True
```

- [ ] **Step 2: Run to verify they fail**

Run: `python scripts/test-refresh-probes.py` — Expected: FAIL, `probes` not importable.

- [ ] **Step 3: Implement `probe`, `Probe`, `ProbeError` and the three probe functions**

A 404 for a year not yet published is a normal negative and continues the walk; any other error raises `ProbeError`.

- [ ] **Step 4: Run to verify they pass**

Run: `python scripts/test-refresh-probes.py` — Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/refresh/probes.py scripts/test-refresh-probes.py
git commit -m "refresh: probes for Census ACS, BEA RPP and DOI rates"
```

---

### Task 3: Runner, dry run only

**Files:**
- Create: `scripts/refresh/runner.py`
- Test: `scripts/test-refresh-runner.py`

**Interfaces:**
- Consumes: `load_sources`, `probe`.
- Produces: `survey(sources: list[Source], *, fetch) -> SurveyResult`. `SurveyResult` is a plain dataclass with `moves: list[Move]`, `failures: list[...]`, `skipped: list[Skipped]`, and **deliberately no** `__len__`, `__bool__`, `__iter__` or `__getitem__` — so `if not result` is always false and every consumer must name `.moves` or `.failures` on purpose. It started as a `list` subclass carrying failures as an attribute; `list(moves)`, `moves[:]`, `sorted(moves)` and comprehensions all silently dropped them, and `if not moves:` read as all-clear when every publisher had failed. That is the shape of the incident this project exists to prevent, so the type now forbids it.
- `Move` has `source_id: str`, `held: str`, `newest: str`, `is_final: bool`, `evidence_url: str`. `Skipped` has `source_id: str`, `due: str | None`, `held_period: str` — a `human_fetch` source is never probed, and Task 6 ages it by `due`.
- `main(argv)` supports `--dry-run`, which surveys and prints and writes nothing.

- [ ] **Step 1: Write the failing test**

```python
moves = survey([acs_held_2024], fetch=stub_census({2025: OK}))
assert len(moves) == 1 and moves[0].newest == "2025"

# held == newest is silence, not a move
moves = survey([acs_held_2025], fetch=stub_census({2025: OK}))
assert moves == []

# a stage-one move is reported but marked not-final
moves = survey([doi_held_2026], fetch=stub_doi(carriers=7))
assert moves[0].is_final is False
```

- [ ] **Step 2: Run to verify it fails** — `python scripts/test-refresh-runner.py`, expect FAIL.

- [ ] **Step 3: Implement `survey` and `main` with `--dry-run`**

- [ ] **Step 4: Run to verify it passes** — Expected: PASS

- [ ] **Step 5: Run the real dry run against live publishers**

Run: `python -m scripts.refresh.runner --dry-run`
Expected: a readable line per source. BEA should report a move pending for 2025 only after 10 Dec 2026; before that it reports no move. Record what it printed in the commit message.

- [ ] **Step 6: Commit**

```bash
git add scripts/refresh/runner.py scripts/test-refresh-runner.py
git commit -m "refresh: survey publishers for newer editions, dry run"
```

---

### Task 4: Fetch, write and reconcile — ACS only

**Files:**
- Modify: `scripts/refresh/runner.py`
- Test: `scripts/test-refresh-runner.py` (extend)

**Interfaces:**
- Produces: `apply(move: Move, *, fetch, dry=False) -> Applied`. `Applied` has `source_id: str`, `old: dict`, `new: dict`, `files_written: list[str]`, `divergences: list[str]` (target paths that still disagree after the write; empty is the healthy case).
- Writes only sources whose `probe == "census_acs1"` in this task. BEA and DOI stay survey-only until their own pass.

- [ ] **Step 1: Write the failing tests**

```python
# happy path: writes both targets and leaves the vintage label consistent
a = apply(acs_move, fetch=stub_census_full())
assert a.new["household"] == 106539.0 and a.new["vintage"] == 2025
assert set(a.files_written) == {"affordability-dashboard.html", "data/burden-constants.json"}

# Review Focus 2 — a short state map aborts the WHOLE write
try:
    apply(acs_move, fetch=stub_census_states(n=12))
    assert False, "short response was written"
except FetchError:
    pass
assert unchanged_on_disk(), "a failed fetch modified a file"

# reconcile — both targets agree once the write lands
a = apply(acs_move, fetch=stub_census_full())
assert a.divergences == []
```

- [ ] **Step 2: Run to verify they fail** — Expected: FAIL.

- [ ] **Step 3: Implement `apply`**

Fetch `B19113_001E` and `B19013_001E` for `state:25`, plus the 50-state + DC household map. Validate the map has 51 entries before writing anything; fewer raises `FetchError`. Write each target with its own line endings preserved. Reconcile: after writing, re-read every target and assert they agree on the figure; report any that do not.

- [ ] **Step 4: Run to verify they pass** — Expected: PASS

- [ ] **Step 5: Address Review Focus 3 — concurrent sessions**

Before committing, `git pull --rebase`; then re-run `survey` for the applied source and abort if the held value changed underneath. Two sessions worked this repo during the design session and one pushed mid-edit, so this is an observed condition, not a hypothetical.

- [ ] **Step 6: Commit**

```bash
git add scripts/refresh/runner.py scripts/test-refresh-runner.py
git commit -m "refresh: fetch, write and reconcile ACS figures"
```

---

### Task 5: Claim registry

**Files:**
- Create: `data/claims.json`
- Create: `scripts/refresh/claims.py`
- Test: `scripts/test-refresh-claims.py`

**Interfaces:**
- Produces: `load_claims(path) -> list[Claim]` and `evaluate(claims: list[Claim], figures: dict[str, float], moved: set[str] = frozenset()) -> list[Verdict]`. `Claim` has `id`, `page`, `text`, `figures: list[str]`, `relation: str | None`. `Verdict` has `claim_id` and `status`, one of `"holds"`, `"broken"`, `"suspect"`. A claim with a `relation` is evaluated; one without is `"suspect"` when any of its `figures` is in `moved`, and otherwise `"holds"`.
- `relation` is a comparison over registered figure ids, e.g. `"ma_auto_expenditure < us_auto_expenditure"`. Evaluate it without `eval` — parse `<lhs> <op> <rhs>` and compare.

- [ ] **Step 1: Write the failing tests**

```python
# the worked example from the spec: this claim was live and inverted
c = Claim(id="ma_auto_cheaper", relation="ma_auto_expenditure < us_auto_expenditure", ...)
v = evaluate([c], {"ma_auto_expenditure": 1326.46, "us_auto_expenditure": 1281.61})[0]
assert v.status == "broken"      # MA is ABOVE; the claim as written is false
v = evaluate([c], {"ma_auto_expenditure": 1200.0, "us_auto_expenditure": 1281.61})[0]
assert v.status == "holds"

# no relation recorded -> suspect when a figure it rests on moved
c2 = Claim(id="x", relation=None, figures=["bea_rpp_state"], ...)
v = evaluate([c2], {"bea_rpp_state": 105.8}, moved={"bea_rpp_state"})[0]
assert v.status == "suspect"
v = evaluate([c2], {"bea_rpp_state": 105.8}, moved=set())[0]
assert v.status == "holds"

# Review Focus 4 — a claim naming an unregistered figure fails loudly
try:
    evaluate([Claim(id="typo", figures=["census_acs1_ma_incom"])], figures={})
    assert False, "unknown figure id was silently skipped"
except UnknownFigure:
    pass
```

- [ ] **Step 2: Run to verify they fail** — Expected: FAIL.

- [ ] **Step 3: Write `data/claims.json` with one real claim per first-pass page and implement `claims.py`**

Register at minimum the MA-vs-US auto comparison, because it is the spec's worked example and it was live and inverted.

- [ ] **Step 4: Run to verify they pass** — Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/claims.json scripts/refresh/claims.py scripts/test-refresh-claims.py
git commit -m "refresh: claim registry with relationship evaluation"
```

---

### Task 6: Reporting and the gate backstop

**Files:**
- Create: `scripts/refresh/report.py`
- Modify: `scripts/check-freshness.py`
- Modify: `scripts/refresh/runner.py`

**Interfaces:**
- Consumes: `Applied`, `Verdict`.
- Produces: `write_receipt(path: Path, run: RunRecord) -> None` and `format_message(run: RunRecord) -> str | None`. **`format_message` returns `None` when nothing moved** — a quiet run sends nothing.
- Receipt lives at `data/refresh-receipt.json`: `{"last_run": ISO date, "unresolved": [source_id], "broken_claims": [claim_id]}`.

- [ ] **Step 1: Write the failing test**

```python
assert format_message(RunRecord(applied=[], verdicts=[])) is None     # silence
msg = format_message(RunRecord(applied=[acs_applied], verdicts=[broken]))
assert "106,539" in msg and "broken" in msg.lower()
```

- [ ] **Step 2: Run to verify it fails** — Expected: FAIL.

- [ ] **Step 3: Implement `write_receipt` and `format_message`; have `runner.main` call both**

- [ ] **Step 4: Modify `check-freshness.py` to read the receipt**

Add a check that fails when any of these hold, each with its own message:
- the receipt is missing, or `last_run` is older than 8 days — **Review Focus 5, the dead-man's switch**. Silence only means all-clear if the loop ran.
- `unresolved` is non-empty — a publisher moved and we could not fetch it.
- `broken_claims` is non-empty — a registered relationship is false.

Keep the existing CRLF line endings. This is what makes stale stop looking like healthy on the channel that already reaches Duncan.

- [ ] **Step 5: Verify both states**

Run: `python scripts/check-freshness.py` with a fresh receipt — Expected: exit 0, receipt row reads ok.
Then with `last_run` backdated 30 days — Expected: non-zero exit naming the dead-man's switch.

- [ ] **Step 6: Commit**

```bash
git add scripts/refresh/report.py scripts/refresh/runner.py scripts/check-freshness.py
git commit -m "refresh: message + receipt, and fail the gate when the loop stops"
```

---

### Task 7: Schedule it

**Files:**
- Create: `.github/workflows/refresh-loop.yml`

- [ ] **Step 1: Write the workflow**

Weekly, plus `workflow_dispatch`. Steps: checkout, run `python -m scripts.refresh.runner`, commit and push any change, then run `scripts/check-freshness.py` so a failure mails Duncan. `CENSUS_API_KEY` from repo secrets.

- [ ] **Step 2: Verify by dispatch**

Run it manually, confirm it completes and the receipt updates.

- [ ] **Step 3: Verify the schedule, not just the dispatch**

Wait for one real scheduled run and confirm it fired. A green `workflow_dispatch` says nothing about whether the cron works — that distinction has already cost this project once.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/refresh-loop.yml
git commit -m "refresh: weekly schedule"
```

---

## Not in this pass

- Writing BEA RPP and DOI figures. They are surveyed and reported; applying them is a later pass once ACS proves the loop end to end.
- `healthcare-dashboard.html`. It holds **41 inline numeric chart arrays**, so it must be converted to a data blob first. That conversion is its own piece of work and should be costed separately.
- Any page beyond `affordability-dashboard.html`.
