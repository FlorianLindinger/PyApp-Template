@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Make the environment match uv.lock exactly.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" sync %*
exit /b %ERRORLEVEL%
