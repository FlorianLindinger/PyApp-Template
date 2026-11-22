:: Preview the splash with the current app name and icon; --seconds controls the duration.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PYAPP_TOOL=show_splash_screen.py"
call "%~dp0src\_run_tool.bat" %*
exit /b %ERRORLEVEL%
