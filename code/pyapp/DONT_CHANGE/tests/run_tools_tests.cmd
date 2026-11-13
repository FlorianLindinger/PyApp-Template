@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Run the "tools" group of the launcher's tests (the maintainer tools in pyapp_tools); see README.md and src\groups.py.
call "%~dp0run_launcher_tests.cmd" tools %*
exit /b %ERRORLEVEL%
