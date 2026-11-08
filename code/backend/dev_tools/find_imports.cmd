@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Find the packages the code imports and add the missing ones after review.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" find-imports %*
exit /b %ERRORLEVEL%
