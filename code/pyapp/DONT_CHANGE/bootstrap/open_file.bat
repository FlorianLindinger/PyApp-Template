@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Opens file %1 in VS Code (or a fork, else Notepad) without starting Python. Setup passes the
rem file as the shortcut argument. Exit code 1 = the file does not exist, the calling B\*.bat
rem then lets the Python action report it. Same editor rules as scripts\console_tools.py (open_in_editor).
if "%~1"=="" exit /b 1
if not exist "%~1" exit /b 1
set "ELECTRON_RUN_AS_NODE="
rem Look for VS Code: "where" lists the places on PATH where code.cmd exists. "for /f" runs a
rem command and handles each line of its output; here it keeps only the first one (%%~fE is the full path).
set "code_cmd="
for /f "delims=" %%E in ('where code.cmd 2^>nul') do if not defined code_cmd set "code_cmd=%%~fE"
if not defined code_cmd goto notepad
rem bin\code.cmd sits one folder below Code.exe; start the .exe directly (no console window).
rem "for %%D in (...)" with one item is a batch trick to turn "a\b\..\.." into a clean full path.
for %%D in ("%code_cmd%\..\..") do set "code_dir=%%~fD"
for %%N in ("Code.exe" "Code - Insiders.exe" "VSCodium.exe" "Cursor.exe") do (
    if exist "%code_dir%\%%~N" (
        set "code_cmd="
        set "code_dir="
        start "" "%code_dir%\%%~N" "%~1"
        exit /b 0
    )
)
rem No known .exe next to it (e.g. another editor's code.cmd): use code.cmd itself.
call "%code_cmd%" "%~1"
exit /b 0

:notepad
start "" notepad.exe "%~1"
exit /b 0
