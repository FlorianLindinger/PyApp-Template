@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Setup passes main.py: open it without Python; the Python action reports a missing file.
call "%~dp0..\bootstrap\open_file.bat" %1 && exit /b 0
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\open_file.py"
call "%~dp0..\bootstrap\run.bat" open_code
exit /b %ERRORLEVEL%
