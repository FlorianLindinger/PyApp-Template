@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Remove declared packages.
set "PYAPP_ALLOW_DOWNLOADS=1"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\scripts\bootstrap\run.bat" remove %*
exit /b %ERRORLEVEL%
