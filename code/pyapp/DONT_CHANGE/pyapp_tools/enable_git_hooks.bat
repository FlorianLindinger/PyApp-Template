:: Runs enable_git_hooks.py with the launcher's Python (the one the template itself resolved).
:: Arguments are passed on; see the docstring of enable_git_hooks.py.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PYAPP_TOOL=enable_git_hooks.py"
call "%~dp0src\_run_tool.bat" %*
exit /b %ERRORLEVEL%
