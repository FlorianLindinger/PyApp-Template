@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Opens file %1 in VS Code (or a fork, else Notepad) without starting Python. Setup passes the
rem file as the shortcut argument. Exit code 1 = the file does not exist, the calling B\*.bat
rem then lets the Python action report it. Same editor rules as scripts\shell_tools.py.
if "%~1"=="" exit /b 1
if not exist "%~1" exit /b 1
set "ELECTRON_RUN_AS_NODE="
set "code_cmd="
for /f "delims=" %%E in ('where code.cmd 2^>nul') do if not defined code_cmd set "code_cmd=%%~fE"
if not defined code_cmd goto notepad
rem bin\code.cmd sits one folder below Code.exe; start the .exe directly (no console window).
for %%D in ("%code_cmd%\..\..") do set "code_dir=%%~fD"
for %%N in ("Code.exe" "Code - Insiders.exe" "VSCodium.exe" "Cursor.exe") do (
    if exist "%code_dir%\%%~N" (
        set "code_cmd="
        set "code_dir="
        start "" "%code_dir%\%%~N" "%~1"
        exit /b 0
    )
)
call "%code_cmd%" "%~1"
exit /b 0

:notepad
start "" notepad.exe "%~1"
exit /b 0
