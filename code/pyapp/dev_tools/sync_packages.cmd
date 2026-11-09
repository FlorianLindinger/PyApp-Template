@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Make the environment match uv.lock exactly.
call "%~dp0..\DONT_CHANGE\run.bat" dev sync %*
exit /b %ERRORLEVEL%
