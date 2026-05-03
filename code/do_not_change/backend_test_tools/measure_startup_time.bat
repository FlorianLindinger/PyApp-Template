@echo off
setlocal

set "HERE=%~dp0"
set "DO_NOT_CHANGE_DIR=%HERE%.."
set "CODE_DIR=%DO_NOT_CHANGE_DIR%\.."
set "BENCHMARK_PY=%DO_NOT_CHANGE_DIR%\specific_scripts\measure_startup_time.py"
set "VENV_PY=%CODE_DIR%\py_env\virt_env\Portable_Scripts\python.bat"
set "DIST_PY=%CODE_DIR%\py_env\py_dist\python.exe"

if exist "%VENV_PY%" (
    call "%VENV_PY%" "%BENCHMARK_PY%" %*
) else if exist "%DIST_PY%" (
    "%DIST_PY%" "%BENCHMARK_PY%" %*
) else (
    echo [Error] No project Python found.
    echo Checked:
    echo   "%VENV_PY%"
    echo   "%DIST_PY%"
    exit /b 1
)

exit /b %ERRORLEVEL%
