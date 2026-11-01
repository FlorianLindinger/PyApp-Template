@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools\reset_packages_imports.py"
call "%~dp0..\DONT_CHANGE\scripts\setup\run_backend_script.bat" %*
exit /b %ERRORLEVEL%
