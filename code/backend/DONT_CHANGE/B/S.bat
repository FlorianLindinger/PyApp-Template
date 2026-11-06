@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Setup passes the user settings file: open it without Python; the Python action reports
rem a disabled or missing settings file.
call "%~dp0..\bootstrap\open_file.bat" %1 && exit /b 0
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\open_file.py"
call "%~dp0..\bootstrap\run.bat" settings
exit /b %ERRORLEVEL%
