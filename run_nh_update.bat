@echo off
REM ============================================================================
REM  NH PrimeMLS daily update — runs on Duncan's PC (residential IP).
REM  PrimeMLS/Cloudflare truncates pulls from GitHub's datacenter IPs, so the
REM  daily refresh runs here instead. Drive-letter agnostic: it operates in this
REM  .bat's own folder (the repo clone), so it works whatever letter the portable
REM  drive gets. Requires a local .env (PRIMEMLS_CLIENT_ID / PRIMEMLS_CLIENT_SECRET).
REM  Scheduled via Task Scheduler; also safe to double-click to run manually.
REM ============================================================================
setlocal
cd /d "%~dp0"

echo [%date% %time%] Syncing repo to origin/main...
git reset --hard origin/main
git pull --quiet

echo Pulling PrimeMLS and rebuilding NH figures...
python update-nh-figures.py all
REM 75 = throttled/truncated pull, nothing written. Expected and self-healing, so
REM exit 0 and let Task Scheduler record a clean run. Anything else is a real error.
REM Checked high-to-low: `errorlevel N` means "N or greater".
if errorlevel 76 goto :realerror
if errorlevel 75 (
  echo SKIPPED: pull was throttled/truncated - nothing committed. Next run will retry.
  exit /b 0
)
if errorlevel 1 goto :realerror
goto :committed

:realerror
echo FAILED: update-nh-figures.py errored - nothing committed.
exit /b 1

:committed

git add data/nh-figures.json data/nh-state-monthly.json
git diff --cached --quiet && (echo No changes to commit. & exit /b 0)

git commit -m "Auto-update: NH PrimeMLS figures"
git push
curl -s "https://purge.jsdelivr.net/gh/duncanburns2013-dot/Massachusetts-Data-Hub@main/data/nh-figures.json" >nul 2>&1
echo Done.
