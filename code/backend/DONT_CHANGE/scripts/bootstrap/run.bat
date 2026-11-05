@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Runs %PYAPP_ENTRY_SCRIPT% with the launcher Python. -I -S: standard library only,
rem so application packages can never break the launcher itself. -X utf8: output and
rem files use UTF-8, so non-ASCII project paths also work when output is redirected.
if not defined PYAPP_ENTRY_SCRIPT (
    echo [Error] Missing launcher entry script.
    exit /b 2
)
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
call "%~dp0ensure_runtime.bat"
if errorlevel 1 goto bootstrap_failed
"%PYAPP_PYTHON%" -I -S -X utf8 "%PYAPP_ENTRY_SCRIPT%" %*
exit /b %ERRORLEVEL%

:bootstrap_failed
if not "%PYAPP_ENTRYPOINT_NO_PAUSE%"=="1" (
    echo Press any key to close this window.
    pause >nul
)
exit /b 1
