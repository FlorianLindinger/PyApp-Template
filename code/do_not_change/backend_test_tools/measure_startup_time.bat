


@echo off
setlocal

set "HERE=%~dp0"
set "DO_NOT_CHANGE_DIR=%HERE%.."
set "CODE_DIR=%DO_NOT_CHANGE_DIR%\.."
set "REPO_DIR=%CODE_DIR%\.."
set "BENCHMARK_PY=%DO_NOT_CHANGE_DIR%\specific_scripts\measure_startup_time.py"
set "VENV_PY=%CODE_DIR%\py_env\virt_env\Portable_Scripts\python.bat"
set "DIST_PY=%CODE_DIR%\py_env\py_dist\python.exe"

rem ==========================
rem ==== benchmark settings ====
rem ==========================

set "RUNS=10"
set "TIMEOUT_SECONDS=10"

rem 1 = measure, 0 = skip
set "MEASURE_WINDOWS_TERMINAL_SHORTCUT=1"
set "MEASURE_TERMINAL_EMULATOR_SHORTCUT=1"
set "MEASURE_BROWSER_SHORTCUT=1"
set "MEASURE_NO_TERMINAL_SHORTCUT=1"
set "MEASURE_DIRECT_PY_DIST=1"
set "MEASURE_DIRECT_GLOBAL_PY=1"

set "BENCHMARK_ARGS=--runs %RUNS% --timeout %TIMEOUT_SECONDS%"
if not "%MEASURE_WINDOWS_TERMINAL_SHORTCUT%"=="1" set BENCHMARK_ARGS=%BENCHMARK_ARGS% --skip-windows-terminal-shortcut
if not "%MEASURE_TERMINAL_EMULATOR_SHORTCUT%"=="1" set BENCHMARK_ARGS=%BENCHMARK_ARGS% --skip-terminal-emulator-shortcut
if not "%MEASURE_BROWSER_SHORTCUT%"=="1" set BENCHMARK_ARGS=%BENCHMARK_ARGS% --skip-browser-shortcut
if not "%MEASURE_NO_TERMINAL_SHORTCUT%"=="1" set BENCHMARK_ARGS=%BENCHMARK_ARGS% --skip-no-terminal-shortcut
if not "%MEASURE_DIRECT_PY_DIST%"=="1" set BENCHMARK_ARGS=%BENCHMARK_ARGS% --skip-py-dist
if not "%MEASURE_DIRECT_GLOBAL_PY%"=="1" set BENCHMARK_ARGS=%BENCHMARK_ARGS% --skip-global

if exist "%VENV_PY%" (
    call "%VENV_PY%" "%BENCHMARK_PY%" %BENCHMARK_ARGS% %*
    set "EXIT_CODE=%ERRORLEVEL%"
) else if exist "%DIST_PY%" (
    "%DIST_PY%" "%BENCHMARK_PY%" %BENCHMARK_ARGS% %*
    set "EXIT_CODE=%ERRORLEVEL%"
) else (
    echo [Error] No project Python found.
    echo Checked:
    echo   "%VENV_PY%"
    echo   "%DIST_PY%"
    set "EXIT_CODE=1"
)

echo.
echo Press any key to exit.
pause > nul

exit /b %EXIT_CODE%
