@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\actions\open_crash_log_folder.py"
call "%~dp0..\scripts\setup\run_backend_script.bat" %*
exit /b %ERRORLEVEL%
