@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Command prompt with the app environment activated and uv on PATH.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" terminal %*
exit /b %ERRORLEVEL%
