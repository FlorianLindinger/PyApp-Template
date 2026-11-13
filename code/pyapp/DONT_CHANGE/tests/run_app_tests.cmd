@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Run the "app" group of the launcher's tests (starting and ending an app); see README.md and src\groups.py.
call "%~dp0run_launcher_tests.cmd" app %*
exit /b %ERRORLEVEL%
