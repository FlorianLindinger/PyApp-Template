@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Show uv, Python, environment and shortcut state.
call "%~dp0..\DONT_CHANGE\run.bat" dev status %*
exit /b %ERRORLEVEL%
