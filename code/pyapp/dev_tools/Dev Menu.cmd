@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Menu with every dev tool.
call "%~dp0..\DONT_CHANGE\B\run.bat" dev menu %*
exit /b %ERRORLEVEL%
