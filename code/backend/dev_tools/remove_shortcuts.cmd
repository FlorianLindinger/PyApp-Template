@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Remove all shortcuts Setup created.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" remove-shortcuts %*
exit /b %ERRORLEVEL%
