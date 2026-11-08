@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Remove declared packages.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" remove %*
exit /b %ERRORLEVEL%
