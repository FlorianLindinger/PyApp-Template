:: Runs make_import_map.py with the launcher's Python (the one the template itself resolved).
:: Arguments are passed on; see the docstring of make_import_map.py.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PYAPP_TOOL=make_import_map.py"
call "%~dp0src\_run_tool.bat" %*
exit /b %ERRORLEVEL%
