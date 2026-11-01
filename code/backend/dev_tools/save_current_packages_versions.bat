@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools\save_current_packages_versions.py"
call "%~dp0..\DONT_CHANGE\batches\bootstrap\run_backend_script.bat" %*
exit /b %ERRORLEVEL%
