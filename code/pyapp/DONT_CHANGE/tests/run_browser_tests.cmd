@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Run the "browser" group of the launcher's tests (the browser terminal, including browser_terminal/tests); see README.md and src\groups.py.
call "%~dp0run_launcher_tests.cmd" browser %*
exit /b %ERRORLEVEL%
