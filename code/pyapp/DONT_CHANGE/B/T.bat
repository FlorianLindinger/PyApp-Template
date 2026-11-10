@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem The Tools shortcut: the dev tools menu for the people using the app (USER_TOOLS in main.py).
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\dev_tools\main.py"
call "%~dp0..\bootstrap\run.bat" tools
exit /b %ERRORLEVEL%
