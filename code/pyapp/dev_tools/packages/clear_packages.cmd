@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Remove every declared package and sync.
call "%~dp0..\..\DONT_CHANGE\B\run.bat" dev clear-packages %*
exit /b %ERRORLEVEL%
