@echo off
rem N.bat: what the "(No-Terminal)" shortcut runs. N = no terminal: meant for GUI apps; prints go
rem to the log, and a window appears only if the app fails.
rem It works like W.bat; see W.bat for the step-by-step start and the batch basics.
setlocal EnableExtensions DisableDelayedExpansion
rem Remember the folder the user started from, unless a calling file already did.
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
rem "no_terminal": run the app without a console window.
set "PYAPP_LAUNCH_MODE=no_terminal"
rem The launcher's Python file that does the start; scripts\bootstrap\run.bat runs it.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\actions\start_program.py"
call "%~dp0..\scripts\bootstrap\run.bat" %*
exit /b %ERRORLEVEL%
