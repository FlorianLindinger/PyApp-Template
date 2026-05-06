@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo WINDOWS CACHES MODULES SO THIS TEST IS PROBABLY ONLY ACCURATE AFTER A FRESH BOOT OR OTHER KIND OF RESTART
echo.

set "PYTHON=py -3.12"
set "MODULES=shutil tkinter multiprocessing pydoc venv asyncio unittest email ssl argparse logging subprocess pathlib tarfile zipfile ctypes json os sys time re"

echo Python:
%PYTHON% -c "import sys; print(sys.version)"
echo.

for /f %%A in ('powershell -NoProfile -Command "[int][math]::Round((Measure-Command { %PYTHON% -c 'pass' }).TotalMilliseconds)"') do set "BASE=%%A"

echo Baseline: %BASE% ms
echo.
echo TotalMs-BaselineMs ModuleName
echo -----------------------

for %%M in (%MODULES%) do (
    for /f %%T in ('powershell -NoProfile -Command "[int][math]::Round((Measure-Command { %PYTHON% -c 'import %%M' }).TotalMilliseconds)"') do set "TOTAL=%%T"

    set /a IMPORT=!TOTAL! - %BASE%

    echo !IMPORT! ms  %%M
)

pause