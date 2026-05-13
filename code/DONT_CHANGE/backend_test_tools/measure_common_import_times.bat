@echo off
setlocal EnableExtensions

set "HERE=%~dp0"
set "DO_NOT_CHANGE_DIR=%HERE%.."
set "CODE_DIR=%DO_NOT_CHANGE_DIR%\.."
set "BACKEND_PY=%DO_NOT_CHANGE_DIR%\P\P.exe"

rem ==========================
rem ==== benchmark settings ====
rem ==========================

set "RUNS=10"

if not exist "%BACKEND_PY%" (
    echo [Error] Backend Python not found:
    echo   "%BACKEND_PY%"
    echo.
    pause
    exit /b 1
)

echo WINDOWS CACHES FILES AND MODULES, SO THIS IS MOST USEFUL AFTER A FRESH BOOT OR RESTART.
echo.
echo Backend Python:
"%BACKEND_PY%" -c "import sys; print(sys.version); print(sys.executable)"
echo.

"%BACKEND_PY%" "%HERE%measure_common_import_times.py" --runs "%RUNS%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Press any key to exit.
pause > nul

exit /b %EXIT_CODE%
