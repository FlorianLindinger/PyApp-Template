@echo off
rem tmp\ is not in Git (caches, locks, run folders): create it on the first start.
if not exist "%~dp0..\tmp\" mkdir "%~dp0..\tmp" 2>nul
rem Sets PYAPP_UV (uv.exe) and PYAPP_PYTHON (the Python that runs the launcher) for the caller.
rem No setlocal on purpose: the variables must reach the calling batch.
rem Fast path: reuse tmp\runtime.cmd while this project folder, developer_settings.py and
rem backend\env\.python-version are unchanged and both executables still exist. Otherwise
rem resolve_runtime.ps1 finds or installs uv and Python.
rem The stamp contains this folder's path (a copied project must not use the original's uv/Python)
rem and the SHA-256 of developer_settings.py (file times only have minute resolution here).

set "PYAPP_STAMP_1="
for /f "skip=1 delims=" %%H in ('certutil.exe -hashfile "%~dp0..\..\developer_settings.py" SHA256 2^>nul') do (
    if not defined PYAPP_STAMP_1 set "PYAPP_STAMP_1=%%H"
)
if not defined PYAPP_STAMP_1 (
    for %%F in ("%~dp0..\..\developer_settings.py") do set "PYAPP_STAMP_1=%%~tF#%%~zF"
)
if exist "%~dp0..\..\env\.python-version" (
    for %%F in ("%~dp0..\..\env\.python-version") do set "PYAPP_STAMP_2=%%~tF#%%~zF"
) else (
    set "PYAPP_STAMP_2=none"
)
set "PYAPP_STAMP=%~dp0#%PYAPP_STAMP_1%#%PYAPP_STAMP_2%"
set "PYAPP_STAMP_1="
set "PYAPP_STAMP_2="
set "PYAPP_CACHED_STAMP="

if exist "%~dp0..\tmp\runtime.cmd" call :load_cache
if not defined PYAPP_CACHED_STAMP goto resolve
if not "%PYAPP_CACHED_STAMP%"=="%PYAPP_STAMP%" goto resolve
if not exist "%PYAPP_PYTHON%" goto resolve
if not exist "%PYAPP_UV%" goto resolve
exit /b 0

:resolve
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0resolve_runtime.ps1" -Stamp "%PYAPP_STAMP%"
if errorlevel 1 exit /b 1
set "PYAPP_CACHED_STAMP="
call :load_cache
if not defined PYAPP_PYTHON (
    echo ERROR  The bootstrap did not record a Python interpreter.
    exit /b 1
)
exit /b 0

:load_cache
rem The cache is UTF-8 and is read with code page 65001, unless its first line says it is
rem plain ASCII (the usual case): then the three chcp calls are skipped.
set "PYAPP_CACHE_HEAD="
set /p PYAPP_CACHE_HEAD=<"%~dp0..\tmp\runtime.cmd"
if "%PYAPP_CACHE_HEAD%"=="rem ascii" (
    set "PYAPP_CACHE_HEAD="
    call "%~dp0..\tmp\runtime.cmd"
    exit /b 0
)
set "PYAPP_CACHE_HEAD="
set "PYAPP_OLD_CP="
for /f "tokens=2 delims=:." %%C in ('chcp') do set "PYAPP_OLD_CP=%%C"
chcp 65001 >nul
call "%~dp0..\tmp\runtime.cmd"
if defined PYAPP_OLD_CP chcp %PYAPP_OLD_CP% >nul
set "PYAPP_OLD_CP="
exit /b 0
