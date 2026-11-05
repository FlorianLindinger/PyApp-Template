@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Delete logs, run diagnostics or old-template folders.
set "PYAPP_ALLOW_DOWNLOADS=1"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" clean %*
exit /b %ERRORLEVEL%
