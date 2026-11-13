@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Run the "setup" group of the launcher's tests (settings, environment, uv and Python); see README.md and src\groups.py.
call "%~dp0run_launcher_tests.cmd" setup %*
exit /b %ERRORLEVEL%
