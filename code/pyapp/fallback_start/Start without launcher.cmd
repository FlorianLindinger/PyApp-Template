@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Fallback start: runs the app's main script WITHOUT the launcher (pyapp\DONT_CHANGE), for when the
rem launcher is broken. Uses the app's environment (generated\.venv) if its Python still starts, otherwise
rem the global default Python. DONT_CHANGE\scripts\actions\start_without_launcher.py shows what it uses and runs
rem the app; it is the only launcher file this uses.
rem Arguments are passed on to the main script.
rem How it chooses Python: 1. the app's environment, if its python.exe still starts;
rem 2. the "py" launcher's default Python; 3. "python" on PATH. Batch basics: see ../DONT_CHANGE/B/W.bat.
rem "&&" below runs the next part only if the command before it succeeded.
title Start without launcher
set "PYAPP_FALLBACK_PYTHON="
set "fallback_script=%~dp0..\DONT_CHANGE\scripts\actions\start_without_launcher.py"
if not exist "%fallback_script%" goto :missing_script
set "venv_python=%~dp0..\generated\.venv\Scripts\python.exe"
set "PYAPP_FALLBACK_VENV=missing"
if exist "%venv_python%" set "PYAPP_FALLBACK_VENV=broken"
if exist "%venv_python%" "%venv_python%" -c "" >nul 2>&1 && (
    set "PYAPP_FALLBACK_PYTHON=%venv_python%"
    set "PYAPP_FALLBACK_VENV=ok"
    set "PYAPP_FALLBACK_SOURCE=venv"
    goto :run
)
rem The py launcher's default Python, then python on PATH (the Microsoft Store stand-in prints nothing).
rem "for /f" runs the command in single quotes and stores its printed line (the Python path) in %%P.
rem 2^>nul hides error messages; the ^ is needed inside the quotes of a "for /f" command.
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
rem After a failure this file waits for a key, so the window stays open even if the fallback script
rem itself cannot start; the variable tells the script not to ask a second time.
set "PYAPP_BATCH_PAUSES_ON_FAILURE=1"
"%PYAPP_FALLBACK_PYTHON%" "%fallback_script%" %*
set "fallback_exit_code=%ERRORLEVEL%"
if "%fallback_exit_code%"=="0" exit /b 0
echo.
echo Press any key to close this window.
pause >nul
exit /b %fallback_exit_code%

:missing_script
echo.
echo  ERROR  The fallback script is missing: %fallback_script%
echo         Restore the DONT_CHANGE folder, e.g. from a release zip or Git.
echo.
echo Press any key to close this window.
pause >nul
exit /b 1
