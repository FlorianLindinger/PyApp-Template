@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Fallback start: runs the app's main script WITHOUT the launcher (pyapp\DONT_CHANGE), for when the
rem launcher is broken. Uses the app's environment (generated\.venv) if its Python still starts, otherwise
rem the global default Python. DONT_CHANGE\actions\start_without_launcher.py shows what it uses and runs
rem the app; it is the only launcher file this uses.
rem Arguments are passed on to the main script.
title Start without launcher
set "PYAPP_FALLBACK_PYTHON="
set "fallback_script=%~dp0DONT_CHANGE\actions\start_without_launcher.py"
if not exist "%fallback_script%" goto :missing_script
set "venv_python=%~dp0generated\.venv\Scripts\python.exe"
set "PYAPP_FALLBACK_VENV=missing"
if exist "%venv_python%" set "PYAPP_FALLBACK_VENV=broken"
if exist "%venv_python%" "%venv_python%" -c "" >nul 2>&1 && (
    set "PYAPP_FALLBACK_PYTHON=%venv_python%"
    set "PYAPP_FALLBACK_VENV=ok"
    set "PYAPP_FALLBACK_SOURCE=venv"
    goto :run
)
rem The py launcher's default Python, then python on PATH (the Microsoft Store stand-in prints nothing).
for /f "delims=" %%P in ('py -c "import sys; print(sys.executable)" 2^>nul') do set "PYAPP_FALLBACK_PYTHON=%%P"
if defined PYAPP_FALLBACK_PYTHON (
    set "PYAPP_FALLBACK_SOURCE=py"
    goto :run
)
for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYAPP_FALLBACK_PYTHON=%%P"
if defined PYAPP_FALLBACK_PYTHON (
    set "PYAPP_FALLBACK_SOURCE=path"
    goto :run
)
echo.
echo  ERROR  No Python found: the app's environment (generated\.venv) is missing or broken, and
echo         there is no global Python (py launcher or python on PATH). Install Python from python.org
echo         or run Setup to repair the launcher.
echo.
echo Press any key to close this window.
pause >nul
exit /b 1

:run
"%PYAPP_FALLBACK_PYTHON%" "%fallback_script%" %*
exit /b %ERRORLEVEL%

:missing_script
echo.
echo  ERROR  The fallback script is missing: %fallback_script%
echo         Restore the DONT_CHANGE folder, e.g. from a release zip or Git.
echo.
echo Press any key to close this window.
pause >nul
exit /b 1
