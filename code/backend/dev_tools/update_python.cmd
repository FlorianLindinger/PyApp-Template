@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Newest patch of the project's Python (and newest minor for python_version = "").
set "PYAPP_ALLOW_DOWNLOADS=1"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" update-python %*
exit /b %ERRORLEVEL%
