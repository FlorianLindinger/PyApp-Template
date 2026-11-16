@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Delete logs, crash logs or per-run diagnostics.
call "%~dp0..\..\DONT_CHANGE\B\run.bat" dev clean %*
exit /b %ERRORLEVEL%
