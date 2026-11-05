@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Upgrade all packages (or the named ones) within their declared limits.
set "PYAPP_ALLOW_DOWNLOADS=1"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\scripts\bootstrap\run.bat" upgrade %*
exit /b %ERRORLEVEL%
