@echo off
rem tmp\ is not in Git (caches, locks, run folders): create it on the first start.
if not exist "%~dp0..\tmp\" mkdir "%~dp0..\tmp" 2>nul
rem Sets PYAPP_UV (uv.exe) and PYAPP_PYTHON (the Python that runs the launcher) for the caller.
rem No setlocal on purpose: the variables must reach the calling batch.
rem Fast path: reuse tmp\runtime.cmd while this project folder, developer_settings.py and
rem pyapp\generated\.python-version are unchanged and both executables still exist. Otherwise
rem resolve_runtime.bat finds or installs uv and Python.
rem The stamp contains this folder's path (a copied project must not use the original's uv/Python),
rem the time and size of developer_settings.py, the lines of the settings the bootstrap reads
rem (config.BOOTSTRAP_SETTINGS) and the content of .python-version. The time has only minute
rem resolution, so an edit of the same length within a minute is only seen through the values.
rem Not a hash: the one tool batch has for that, certutil, is distrusted by antivirus programs,
rem and this runs on every launch. "for /f" reads the file without starting another program.

for %%F in ("%~dp0..\..\developer_settings.py") do set "PYAPP_STAMP_1=%%~tF#%%~zF"
for %%N in (1 2 3 4 5 6 7 8) do set "PYAPP_S_%%N="
rem Validation keeps these settings unindented one-line literals; "name: type = value" also works.
rem Like Python, the last assignment counts. A trailing comment is part of the value: harmless.
for /f "usebackq eol=# tokens=1,* delims=:= " %%A in ("%~dp0..\..\developer_settings.py") do (
    if "%%A"=="python_version" set "PYAPP_S_1=%%B"
    if "%%A"=="python_source" set "PYAPP_S_2=%%B"
    if "%%A"=="uv_prefer" set "PYAPP_S_3=%%B"
    if "%%A"=="uv_install_if_missing" set "PYAPP_S_4=%%B"
    if "%%A"=="uv_version" set "PYAPP_S_5=%%B"
    if "%%A"=="uv_user_python_visible_globally" set "PYAPP_S_6=%%B"
    if "%%A"=="uv_cache" set "PYAPP_S_7=%%B"
    if "%%A"=="use_system_certificates" set "PYAPP_S_8=%%B"
)
set "PYAPP_STAMP_2=none"
if exist "%~dp0..\..\generated\.python-version" set /p PYAPP_STAMP_2=<"%~dp0..\..\generated\.python-version"
rem The stamp is compared and passed on in quotes, so it must not contain any.
if defined PYAPP_S_1 set "PYAPP_S_1=%PYAPP_S_1:"=%"
if defined PYAPP_S_2 set "PYAPP_S_2=%PYAPP_S_2:"=%"
if defined PYAPP_S_3 set "PYAPP_S_3=%PYAPP_S_3:"=%"
if defined PYAPP_S_4 set "PYAPP_S_4=%PYAPP_S_4:"=%"
if defined PYAPP_S_5 set "PYAPP_S_5=%PYAPP_S_5:"=%"
if defined PYAPP_S_6 set "PYAPP_S_6=%PYAPP_S_6:"=%"
if defined PYAPP_S_7 set "PYAPP_S_7=%PYAPP_S_7:"=%"
if defined PYAPP_S_8 set "PYAPP_S_8=%PYAPP_S_8:"=%"
if defined PYAPP_STAMP_2 set "PYAPP_STAMP_2=%PYAPP_STAMP_2:"=%"
set "PYAPP_STAMP=%~dp0#%PYAPP_STAMP_1%#%PYAPP_STAMP_2%#%PYAPP_S_1%#%PYAPP_S_2%#%PYAPP_S_3%#%PYAPP_S_4%#%PYAPP_S_5%#%PYAPP_S_6%#%PYAPP_S_7%#%PYAPP_S_8%"
for %%N in (1 2 3 4 5 6 7 8) do set "PYAPP_S_%%N="
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
rem The stamp goes over as PYAPP_STAMP, not as an argument: "call" would expand a "%" or "^" in it again.
call "%~dp0resolve_runtime.bat"
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
