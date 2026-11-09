@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Upgrade all packages (or the named ones) within their declared limits.
call "%~dp0..\DONT_CHANGE\run.bat" dev upgrade %*
exit /b %ERRORLEVEL%
