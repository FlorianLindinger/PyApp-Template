:: Runs release.py with the launcher's Python (the one the template itself resolved).
:: No "run again" here: Enter would bump the version a second time.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0..\bootstrap\ensure_runtime.bat"
if errorlevel 1 (
    pause
    exit /b 1
)
"%PYAPP_PYTHON%" "%~dp0src\release.py" %*
set "exit_code=%ERRORLEVEL%"
echo.
pause
exit /b %exit_code%
