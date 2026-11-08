@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Write backend\requirements.txt from uv.lock.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" export %*
exit /b %ERRORLEVEL%
