@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\stop_program.py"
call "%~dp0..\bootstrap\run.bat" %*
exit /b %ERRORLEVEL%
