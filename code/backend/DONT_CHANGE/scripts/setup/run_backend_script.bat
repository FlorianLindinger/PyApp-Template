@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_ENTRY_SCRIPT (
    echo [Error] Missing backend entry script.
    exit /b 2
)
call "%~dp0ensure_backend_python.bat"
if errorlevel 1 exit /b 1
"%python_exe%" "%PYAPP_ENTRY_SCRIPT%" %*
exit /b %ERRORLEVEL%
