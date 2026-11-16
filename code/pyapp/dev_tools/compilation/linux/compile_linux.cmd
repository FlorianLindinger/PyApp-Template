@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0..\..\..\DONT_CHANGE\B\run.bat" dev compile-linux %*
exit /b %ERRORLEVEL%
