:: Runs check_git_leaks.py with the launcher's Python (the one the template itself resolved).
:: Arguments are passed on; see the docstring of check_git_leaks.py.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PYAPP_TOOL=check_git_leaks.py"
call "%~dp0src\_run_tool.bat" %*
exit /b %ERRORLEVEL%
