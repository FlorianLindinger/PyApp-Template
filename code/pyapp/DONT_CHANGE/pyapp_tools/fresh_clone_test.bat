:: Runs fresh_clone_test.py with the launcher's Python (the one the template itself resolved).
:: Arguments are passed on; see the docstring of fresh_clone_test.py.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PYAPP_TOOL=fresh_clone_test.py"
call "%~dp0src\_run_tool.bat" %*
exit /b %ERRORLEVEL%
