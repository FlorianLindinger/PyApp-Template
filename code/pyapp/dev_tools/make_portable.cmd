@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Put uv, Python and packages inside this folder for offline use.
call "%~dp0..\DONT_CHANGE\run.bat" dev make-portable %*
exit /b %ERRORLEVEL%
