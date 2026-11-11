:: Runs get_import_times.py with the launcher's Python (the one the template itself resolved).
:: Arguments are passed on; see the docstring of get_import_times.py.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PYAPP_TOOL=get_import_times.py"
call "%~dp0src\_run_tool.bat" %*
exit /b %ERRORLEVEL%
