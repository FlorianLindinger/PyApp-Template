@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
set "PYAPP_LAUNCH_MODE=terminal"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\start_program.py"
call "%~dp0..\bootstrap\run.bat" %*
exit /b %ERRORLEVEL%
