@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Run the "files" group of the launcher's tests (static checks of the shipped files); see README.md and src\groups.py.
call "%~dp0run_launcher_tests.cmd" files %*
exit /b %ERRORLEVEL%
