' run-hidden.vbs - launch a .bat with genuinely no console window.
'
' Task Scheduler's own "Hidden" checkbox does not hide a .bat: cmd.exe still
' creates a console host, which is what flashed on screen four times an hour in
' September. powershell -WindowStyle Hidden has the same problem. wscript has no
' console of its own, and Run(..., 0, ...) starts the child hidden, so nothing
' is ever drawn.
'
' Usage:  wscript //B run-hidden.vbs <batch file> <log file>
Option Explicit
Dim args, bat, logf, fso, sh, cmd
Set args = WScript.Arguments
If args.Count < 2 Then WScript.Quit 2
bat  = args(0)
logf = args(1)

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

' The repo lives on an external drive. If it is not mounted the task must say so
' in the log rather than exit 0 and look like a clean run -- a scheduled job that
' reports success while writing nothing is the exact failure this repo keeps
' finding in its own feeds.
If Not fso.FileExists(bat) Then
    Dim f
    On Error Resume Next
    Set f = fso.OpenTextFile(logf, 8, True)
    If Err.Number = 0 Then
        f.WriteLine "[" & Now & "] MISSING: " & bat & " - drive not mounted? Nothing run."
        f.Close
    End If
    WScript.Quit 3
End If

' 0 = hidden window, True = wait, so the task's Last Run Result is the bat's.
cmd = "cmd /c """"" & bat & """ >> """ & logf & """ 2>&1"""
WScript.Quit sh.Run(cmd, 0, True)
