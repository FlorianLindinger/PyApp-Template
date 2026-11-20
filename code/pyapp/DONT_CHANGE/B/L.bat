@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem L.bat: what the "(Logs)" shortcut runs: opens the log folder in Explorer.
rem See W.bat for the batch basics. %1 is the first argument: Setup puts the folder there.
rem Setup passes the log folder: open it without Python. Otherwise (a log path relative to
rem the start folder, or with date codes) the Python action resolves it.
rem "&&" runs the next command only if the one before succeeded (exit code 0). So: if the
rem fast path could open the folder, stop here; otherwise continue below and let Python explain why not.
call "%~dp0..\bootstrap\open_folder.bat" %1 && exit /b 0
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\open_folder.py"
call "%~dp0..\bootstrap\run.bat" logs
exit /b %ERRORLEVEL%
