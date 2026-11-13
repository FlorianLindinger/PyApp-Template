@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Show the main packages, their dependencies and what is installed differently from uv.lock.
call "%~dp0..\DONT_CHANGE\run.bat" dev list-packages %*
exit /b %ERRORLEVEL%
