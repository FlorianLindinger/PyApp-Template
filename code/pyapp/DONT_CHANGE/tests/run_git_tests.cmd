@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Run the "git" group of the launcher's tests (the Git hooks and their checks); see README.md and src\groups.py.
call "%~dp0run_launcher_tests.cmd" git %*
exit /b %ERRORLEVEL%
