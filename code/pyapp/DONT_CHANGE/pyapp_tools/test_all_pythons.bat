:: Runs test_all_pythons.py with the launcher's Python (the one the template itself resolved).
:: Arguments are passed on; see the docstring of test_all_pythons.py.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PYAPP_TOOL=test_all_pythons.py"
call "%~dp0src\_run_tool.bat" %*
exit /b %ERRORLEVEL%
