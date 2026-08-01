@echo off
setlocal EnableExtensions

:: ==========================
:: benchmark settings

set "RUNS=10"
set "HERE=%~dp0"
set "code_dir=%HERE%..\..\..\.."
set "FILES=backend.DONT_CHANGE.settings.backend_settings backend.DONT_CHANGE.scripts.common_code"

set "HELPER_FILE=%HERE%..\..\scripts\backend_tools\measure_file_import_times.py"
set "BACKEND_PY=%HERE%..\..\backend_python\python.exe"

:: ==========================

if not exist "%BACKEND_PY%" (
    echo [Error] Backend Python not found:
    echo   "%BACKEND_PY%"
    echo.
    pause
    exit /b 1
)

echo     NOTE: WINDOWS CACHES MODULES SO THIS TEST IS PROBABLY ONLY ACCURATE AFTER A FRESH BOOT OR OTHER KIND OF RESTART
echo.
echo Backend Python:
"%BACKEND_PY%" -c "import sys; print(sys.version); print(sys.executable)"
echo.

"%BACKEND_PY%" "%HELPER_FILE%" "%RUNS%" "%code_dir%" %FILES%
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Press any key to exit.
pause > nul

exit /b %EXIT_CODE%
