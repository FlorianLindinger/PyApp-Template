:: Shared body of the pyapp_tools\*.bat wrappers: runs src\%PYAPP_TOOL% with the launcher's Python
:: (the one the template itself resolved), passing on the wrapper's arguments, and offers to run again.
@echo off
setlocal EnableExtensions DisableDelayedExpansion
:again
call "%~dp0..\..\bootstrap\ensure_runtime.bat"
if errorlevel 1 (
    pause
    exit /b 1
)
"%PYAPP_PYTHON%" "%~dp0%PYAPP_TOOL%" %*
set "exit_code=%ERRORLEVEL%"
echo.
:: Not set /p or pause: without a keyboard (no more input) this must end instead of repeating forever.
"%PYAPP_PYTHON%" -I -S -c "input('Press Enter to run again (close this window to stop). ')" 2>nul
if errorlevel 1 exit /b %exit_code%
cls
goto again
