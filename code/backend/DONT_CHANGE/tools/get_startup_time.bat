:: Runs get_startup_time.py with the launcher's Python (the one the template itself resolved).
:: Arguments are passed on; see the docstring of get_startup_time.py.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0..\bootstrap\ensure_runtime.bat"
if errorlevel 1 exit /b 1
"%PYAPP_PYTHON%" "%~dp0..\scripts\tools\get_startup_time.py" %*
set "exit_code=%ERRORLEVEL%"
pause
exit /b %exit_code%
