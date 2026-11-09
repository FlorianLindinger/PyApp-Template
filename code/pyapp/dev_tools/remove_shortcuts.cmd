@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Remove all shortcuts Setup created.
call "%~dp0..\DONT_CHANGE\run.bat" dev remove-shortcuts %*
exit /b %ERRORLEVEL%
