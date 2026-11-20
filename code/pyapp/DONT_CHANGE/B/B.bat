@echo off
rem B.bat: what the "(Browser)" shortcut runs. Like W.bat, but the program's console is shown in a
rem browser tab instead of a console window. See W.bat for the step-by-step start and the batch basics.
setlocal EnableExtensions DisableDelayedExpansion
rem Remember the folder the user started from, unless a calling file already did.
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
rem "browser": the console runs in a browser tab; browser_terminal\ is the small local web server for it.
set "PYAPP_LAUNCH_MODE=browser"
rem The launcher's Python file that does the start; bootstrap\run.bat runs it.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\start_program.py"
call "%~dp0..\bootstrap\run.bat" %*
exit /b %ERRORLEVEL%
