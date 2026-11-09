@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Write pyapp\requirements.txt from uv.lock.
call "%~dp0..\DONT_CHANGE\run.bat" dev export %*
exit /b %ERRORLEVEL%
