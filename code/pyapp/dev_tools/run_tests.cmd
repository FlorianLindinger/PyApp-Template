@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Run the app's own tests (code\tests, code\pyapp\tests) with the app's environment.
call "%~dp0..\DONT_CHANGE\run.bat" dev run-tests %*
exit /b %ERRORLEVEL%
