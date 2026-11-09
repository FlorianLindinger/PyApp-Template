@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Command prompt with the app environment activated and uv on PATH.
call "%~dp0..\DONT_CHANGE\run.bat" dev terminal %*
exit /b %ERRORLEVEL%
