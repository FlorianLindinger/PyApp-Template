@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\shortcut_targets\stop_program.py"
call "%~dp0helper_scripts\run_backend_script.bat" %*
exit /b %ERRORLEVEL%
