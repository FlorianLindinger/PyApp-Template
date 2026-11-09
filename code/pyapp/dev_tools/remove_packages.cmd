@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Remove declared packages.
call "%~dp0..\DONT_CHANGE\run.bat" dev remove %*
exit /b %ERRORLEVEL%
