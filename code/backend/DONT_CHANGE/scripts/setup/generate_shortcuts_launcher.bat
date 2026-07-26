:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: move to folder of this file:
cd /d "%~dp0"

:: ===========================
:: local variables

set "ensure_backend_python_script=ensure_backend_python.bat"
set "shortcut_generator_script=generate_shortcuts.py"
set "terminal_title=Generating Shortcuts"

:: ===========================
:: code execution

:: change title:
title %terminal_title%

:: install backend Python if needed and receive its path in python_exe:
call "%ensure_backend_python_script%"
:: exit on failure (print and confirm close handled in child):
if not "%ERRORLEVEL%"=="0" (
    exit 1
)

:: generate shortcuts:
"%python_exe%" "%shortcut_generator_script%"
set "exit_code=%ERRORLEVEL%"

:: exit if success:
if "%exit_code%"=="0" (
    exit /b 0
)

:: print and confirm to close on failure:
echo [Error] Shortcut generation failed. Aborting. Press any key to exit.
pause > nul
exit /b %exit_code%
