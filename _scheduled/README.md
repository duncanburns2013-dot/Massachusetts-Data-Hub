# Scheduled tasks on Duncan's PC

Two feeds cannot run from GitHub Actions, so they run here instead. This folder
holds the launcher and the logs; the jobs themselves are the `run_*.bat` files
in the repo root.

## Why these run locally at all

| Feed | Runs where | Why |
|---|---|---|
| CBP encounters | **this machine, every 4 weeks** | cbp.gov's bot filter 403s GitHub's runners even through curl with a full browser header set. Re-verified 2026-09-24 on a hosted runner: every page blocked. A residential IP works. |
| NH PrimeMLS | **GitHub Actions, daily** | The cloud run works — 13 of the last 14 scheduled runs pulled real data. `run_nh_update.bat` is kept as a manual fallback for days CI is throttled, but it is NOT scheduled; a second daily writer is what drifted MASTER_DATA.md out of sync with its feed on 2026-10-03. |

## Why the VBS shim

Task Scheduler's own "Hidden" setting does not hide a `.bat`: cmd.exe still
creates a console host and it flashes on screen. `powershell -WindowStyle Hidden`
has the same problem — that combination put a window on screen four times an
hour in September. `wscript //B` has no console of its own and
`WshShell.Run(cmd, 0, True)` starts the child hidden, so nothing is drawn, and
the task still gets the batch file's exit code as its Last Run Result.

`run-hidden.vbs` also logs and exits 3 when the batch file is missing, rather
than exiting 0. A scheduled job that reports success while writing nothing is
the exact silent-staleness failure the freshness watchdog exists to catch.

## Logon type

The task runs **only when logged on**, deliberately. Git Credential Manager
keeps the GitHub token under DPAPI keyed to the interactive session, so a task
running without the password cannot read it and `git push` fails. Running
interactively keeps the push working; GitHub Actions is the redundant path for
everything that can run there.

## Re-creating the task

```powershell
$vbs = 'F:\Massachusetts-Data-Hub\_scheduled\run-hidden.vbs'
$bat = 'F:\Massachusetts-Data-Hub\run_cbp_update.bat'
$log = 'F:\Massachusetts-Data-Hub\_scheduled\cbp-update.log'
$act = New-ScheduledTaskAction -Execute 'wscript.exe' `
         -Argument ('//B //NoLogo "{0}" "{1}" "{2}"' -f $vbs,$bat,$log) `
         -WorkingDirectory 'F:\Massachusetts-Data-Hub'
$trg = New-ScheduledTaskTrigger -Weekly -WeeksInterval 4 -DaysOfWeek Wednesday -At 9:15am
$set = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
         -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
$prn = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
         -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'MA Data Hub - CBP monthly' `
  -Action $act -Trigger $trg -Settings $set -Principal $prn
```

## Requirements

- `.env` in the repo root. CBP needs no key; `PRIMEMLS_CLIENT_ID` /
  `PRIMEMLS_CLIENT_SECRET` are needed only if the NH batch is run by hand.
- The repo is on an external drive. If F: is not mounted when the task fires it
  logs "drive not mounted" and exits 3 instead of reporting a clean run.
