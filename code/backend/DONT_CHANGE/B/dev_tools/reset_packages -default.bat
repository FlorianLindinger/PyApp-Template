@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\..\scripts\dev_tools\reset_packages -default.py"
call "%~dp0..\helper_scripts\run_backend_script.bat" %*
exit /b %ERRORLEVEL%
