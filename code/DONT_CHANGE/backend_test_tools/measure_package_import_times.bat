@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: ==========================
:: benchmark settings

set "PYTHON=%~dp0..\backend_python\python.exe"
set "MODULES=os sys subprocess shutil rich traceback ctypes time re tempfile html.parser urllib.parse urllib.request urllib.error uuid signal threading"

:: ==========================

echo     NOTE: WINDOWS CACHES MODULES SO THIS TEST IS PROBABLY ONLY ACCURATE AFTER A FRESH BOOT OR OTHER KIND OF RESTART
echo.

if not exist "%PYTHON%" (
    echo [Error] Backend Python not found:
    echo   "%PYTHON%"
    echo.
    pause
    exit /b 1
)

echo Python:
"%PYTHON%" -c "import sys; print(sys.version); print(sys.executable)"
echo.

for /f %%A in ('powershell -NoProfile -Command "[int][math]::Round((Measure-Command { & '%PYTHON%' -c 'pass' }).TotalMilliseconds)"') do set "BASE=%%A"

echo Baseline: %BASE% ms
echo.
echo TotalMs-BaselineMs ModuleName
echo -----------------------

for %%M in (%MODULES%) do (
    for /f %%T in ('powershell -NoProfile -Command "[int][math]::Round((Measure-Command { & '%PYTHON%' -c 'import %%M' }).TotalMilliseconds)"') do set "TOTAL=%%T"

    set /a IMPORT=!TOTAL! - %BASE%

    echo !IMPORT! ms  %%M
)

pause
