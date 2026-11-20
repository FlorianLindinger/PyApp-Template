@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem M.bat: what the "(Edit-Code)" shortcut runs: opens the main script in VS Code, or Notepad.
rem See W.bat for the batch basics. %1 is the first argument: Setup puts the script's path there.
rem Setup passes main.py: open it without Python; the Python action reports a missing file.
rem "&&" runs the next command only if the one before succeeded (exit code 0). So: if the
rem fast path could open the file, stop here; otherwise continue below and let Python explain why not.
call "%~dp0..\bootstrap\open_file.bat" %1 && exit /b 0
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\open_file.py"
call "%~dp0..\bootstrap\run.bat" open_code
exit /b %ERRORLEVEL%
