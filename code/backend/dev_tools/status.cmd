@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Show uv, Python, environment and shortcut state.
set "PYAPP_ALLOW_DOWNLOADS=1"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\scripts\bootstrap\run.bat" status %*
exit /b %ERRORLEVEL%
