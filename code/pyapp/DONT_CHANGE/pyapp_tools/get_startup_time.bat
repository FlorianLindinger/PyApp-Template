:: Runs get_startup_time.py with the launcher's Python (the one the template itself resolved).
:: Arguments are passed on; see the docstring of get_startup_time.py.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PYAPP_TOOL=get_startup_time.py"
call "%~dp0src\_run_tool.bat" %*
exit /b %ERRORLEVEL%
