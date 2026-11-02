# Weekly health check for the Massachusetts Data Hub. REPORT ONLY.
#
# Why this file exists, 2026-11-02: the weekly scheduled task used to have Claude
# compose its own multi-statement PowerShell on every run. The allowlist matches
# command PREFIXES, so a script beginning "if (-not (Test-Path ..." matched none
# of the 26 PowerShell(git ... *) rules and raised a permission prompt. A
# scheduled run has no human to answer it, so the run parked forever and the task
# held its lock: 2026-10-05 sat 5 days, 2026-10-19 sat 36 hours, 2026-11-02 was
# killed by hand after 2 hours. One fixed command string is one allow rule, and
# the prompt never happens again. Do not go back to composing this inline, and
# keep this file's invocation EXACTLY as SKILL.md spells it.
#
# This script only gathers. It makes no judgements and writes nothing to the
# repo: Claude reads the output and writes the report.
#
# NEVER add anything here whose name starts with update-, and never pass
# --update to check-stats-documented.py. Those write.

$ErrorActionPreference = 'Continue'

# Native executables (git, node, gh, python) write progress and warnings to
# stderr. Piping them with "2>&1 |" wraps every such line in a PowerShell
# ErrorRecord (NativeCommandError) and sets $? false even on exit 0, which makes
# a clean run read as a broken one. Call them bare and let stderr through.

# A credential prompt hangs exactly like the permission prompt this file exists
# to kill, and would be invisible for the same reason. Refuse to ask instead.
$env:GIT_TERMINAL_PROMPT = '0'
$env:GCM_INTERACTIVE = 'never'

$Repo = 'F:\Massachusetts-Data-Hub'

function Section([string]$Name) { Write-Output ''; Write-Output "=== SECTION: $Name ===" }
function Code([int]$n)          { Write-Output "--- exit: $n ---" }

Write-Output "weekly-health.ps1  run at $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) UTC"

Section 'REPO'
if (-not (Test-Path $Repo)) {
    Write-Output 'F: NOT MOUNTED'
    Code 1
    Write-Output ''
    Write-Output 'ABORTED: the canonical clone is unreachable. Do not fall back to the C: backup mirror or re-clone.'
    exit 1
}
Set-Location $Repo
git fetch origin
Write-Output "fetch exit=$LASTEXITCODE"
# --ff-only, never --rebase: a rebase stops on conflict and waits for a human.
git pull --ff-only origin main
$pullCode = $LASTEXITCODE
Write-Output "pull exit=$pullCode"
if ($pullCode -ne 0) {
    Write-Output 'DIVERGED: local main and origin/main have diverged. Every figure below is from an UN-UPDATED clone. Report this as a failure, but the remaining checks still ran and still count.'
}
git status -sb | Select-Object -First 5 | Write-Output
git log -1 --format='%h %ci %s' | Write-Output
Code $pullCode

Section 'FRESHNESS'
python scripts/check-freshness.py
Code $LASTEXITCODE

Section 'CONSISTENCY'
python scripts/check-consistency.py
Code $LASTEXITCODE

Section 'REPOS'
python scripts/check-repos.py
Code $LASTEXITCODE

Section 'STATS-DOCUMENTED'
python scripts/check-stats-documented.py
Code $LASTEXITCODE

# Both suites print "metro charts NOT updated" / "comparison box NOT updated".
# Those are negative-case assertions PASSING. Judge only the final
# "All checks passed" line and the exit code; do not report the warnings.
Section 'JS-TEST-METRO'
node --use-system-ca scripts/test-metro-charts.mjs
Code $LASTEXITCODE

Section 'JS-TEST-COMPARISON'
node --use-system-ca scripts/test-comparison-box.mjs
Code $LASTEXITCODE

Section 'WORKFLOW-HISTORY'
# 40 runs, enough to see a streak rather than just the latest morning.
gh run list --limit 40 --json name,conclusion,createdAt,event -q '.[] | [.createdAt, .event, .conclusion, .name] | @tsv'
Code $LASTEXITCODE

Section 'CBP'
# Report-only. Do NOT run update-cbp-encounters.py.
python -c "import json,datetime; d=json.load(open('data/cbp-encounters-latest.json',encoding='utf-8')); fy=d['fy_totals']; k=sorted(fy)[-1]; last=fy[k]['last_month']; print('newest month in json :',last); print('months reported     :',fy[k]['months_reported'],'of',k); print('json fetched_at     :',d['fetched_at'][:10]); print('today               :',datetime.date.today().isoformat())"
Write-Output 'raw CBP exports on disk (mtime, name):'
Get-ChildItem "$Repo\data\_raw_cbp" -Filter *.csv -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Output ("  {0:yyyy-MM-dd}  {1}" -f $_.LastWriteTime, $_.Name) }
Write-Output 'If a hand download is needed: https://www.cbp.gov/document/stats/nationwide-encounters'
Write-Output 'Drop it in data\_raw_cbp and RENAME OFF the browser _0 suffix, which breaks the nationwide-encounters-*-aor.csv glob.'
Code 0

Section 'PRIT'
# Report-only. Do NOT run update-prit.py; it only writes on a fiscal-year close.
python -c "import json,datetime; d=json.load(open('data/prit-latest.json',encoding='utf-8')); print('fiscal_year :',d['fiscal_year']); print('as_of       :',d['as_of']); print('verified    :',d.get('verified')); t=datetime.date.today(); print('today       :',t.isoformat()); print('NOTE: it is month %d. FY figures land in PRIM August quarterly update; if Sep or later and fiscal_year is still the prior FY, say so.' % t.month)"
Code 0

Write-Output ''
Write-Output '=== SECTION: END ==='
