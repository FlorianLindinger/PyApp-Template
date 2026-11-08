@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Menu with every dev tool.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" menu %*
exit /b %ERRORLEVEL%
