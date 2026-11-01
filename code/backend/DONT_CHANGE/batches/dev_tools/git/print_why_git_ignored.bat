@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\..\..\scripts\dev_tools\git\print_why_git_ignored.py"
call "%~dp0..\..\bootstrap\run_backend_script.bat" %*
exit /b %ERRORLEVEL%
