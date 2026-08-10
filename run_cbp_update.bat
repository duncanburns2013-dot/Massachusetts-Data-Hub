@echo off
REM ============================================================================
REM  CBP Border Patrol monthly update - runs on Duncan's PC (residential IP).
REM  cbp.gov's bot filter 403s GitHub's datacenter IPs even with a browser UA
REM  (verified from CI on 2026-08-07), so the refresh runs here, exactly like
REM  run_nh_update.bat. The GitHub workflow stays as a retry path: it reports a
REM  neutral skip when it is blocked, so it never mails a failure.
REM  Drive-letter agnostic: it operates in this .bat's own folder (the repo
REM  clone). No API key needed. Monthly is enough - CBP publishes monthly.
REM  Scheduled via Task Scheduler; also safe to double-click to run manually.
REM ============================================================================
setlocal
cd /d "%~dp0"

echo [%date% %time%] Syncing repo to origin/main...
git reset --hard origin/main
git pull --quiet

echo Fetching CBP monthly tables and rebuilding the immigration series...
python update-cbp-encounters.py
REM 75 = the source blocked us, nothing written. Expected and self-healing, so
REM exit 0 and let Task Scheduler record a clean run. Anything else is real.
REM Checked high-to-low: `errorlevel N` means "N or greater".
if errorlevel 76 goto :realerror
if errorlevel 75 (
  echo SKIPPED: cbp.gov blocked the fetch - nothing committed. Next run will retry.
  exit /b 0
)
if errorlevel 1 goto :realerror
goto :committed

:realerror
echo FAILED: update-cbp-encounters.py errored - nothing committed.
exit /b 1

:committed

git add immigration-dashboard.html data/cbp-encounters-latest.json
git diff --cached --quiet && (echo No changes to commit. & exit /b 0)

git commit -m "Auto-update: CBP encounter data"
git push
curl -s "https://purge.jsdelivr.net/gh/duncanburns2013-dot/Massachusetts-Data-Hub@main/data/cbp-encounters-latest.json" >nul 2>&1
echo Done.
