@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\..\scripts\icons\generate_PNGs_to_be_replaced.py"
call "%~dp0..\bootstrap\run_backend_script.bat" %*
exit /b %ERRORLEVEL%
