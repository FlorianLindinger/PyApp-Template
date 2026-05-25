@echo off
setlocal EnableExtensions

:: ==========================
:: benchmark settings

set "RUNS=10"
set "specific_scripts_dir=%~dp0..\specific_scripts"
set "FILES=common_variables common_code launcher_common"

set "HELPER_FILE=%HERE%helper_scripts\measure_file_import_times.py"
set "BACKEND_PY=%HERE%..\P\P.exe"

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

"%BACKEND_PY%" "%HELPER_FILE%" "%RUNS%" "%specific_scripts_dir%" %FILES%
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Press any key to exit.
pause > nul

exit /b %EXIT_CODE%
