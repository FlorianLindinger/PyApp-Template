@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Add packages (asks for names, or pass them: add_packages.cmd requests numpy).
set "PYAPP_ALLOW_DOWNLOADS=1"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\scripts\bootstrap\run.bat" add %*
exit /b %ERRORLEVEL%
