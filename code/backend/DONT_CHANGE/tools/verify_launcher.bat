:: Runs verify_launcher.py with the launcher's Python (the one the template itself resolved).
:: Arguments are passed on; see the docstring of verify_launcher.py.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0..\bootstrap\ensure_runtime.bat"
if errorlevel 1 exit /b 1
"%PYAPP_PYTHON%" "%~dp0..\scripts\tools\verify_launcher.py" %*
set "exit_code=%ERRORLEVEL%"
pause
exit /b %exit_code%
