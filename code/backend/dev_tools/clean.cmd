@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Delete logs, crash logs or per-run diagnostics.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" clean %*
exit /b %ERRORLEVEL%
