@echo off
rem Sets PYAPP_UV (uv.exe) and PYAPP_PYTHON (the Python that runs the launcher) for the caller.
rem No setlocal on purpose: the variables must reach the calling batch.
rem Fast path: reuse tmp\runtime.cmd while developer_settings.py and backend\.python-version are unchanged
rem and both executables still exist. Otherwise resolve_runtime.ps1 finds or installs uv and Python.

set "PYAPP_STAMP="
for %%F in ("%~dp0..\..\developer_settings.py") do set "PYAPP_STAMP=%%~tF#%%~zF"
if exist "%~dp0..\..\.python-version" (
    for %%F in ("%~dp0..\..\.python-version") do set "PYAPP_STAMP_2=%%~tF#%%~zF"
) else (
    set "PYAPP_STAMP_2=none"
)
set "PYAPP_STAMP=%PYAPP_STAMP%#%PYAPP_STAMP_2%"
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
    echo [Error] The bootstrap did not record a Python interpreter.
    exit /b 1
)
exit /b 0

:load_cache
rem The cache is UTF-8 so non-ASCII project paths survive; read it with code page 65001.
set "PYAPP_OLD_CP="
for /f "tokens=2 delims=:." %%C in ('chcp') do set "PYAPP_OLD_CP=%%C"
chcp 65001 >nul
call "%~dp0..\tmp\runtime.cmd"
if defined PYAPP_OLD_CP chcp %PYAPP_OLD_CP% >nul
set "PYAPP_OLD_CP="
exit /b 0
