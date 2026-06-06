:: disable printing of commands
@echo off

:: make variables local
setlocal

:: move to folder of this file
cd /d "%~dp0"

:: ===========================
:: local variables

set "python_exe=..\..\backend_python\python.exe"
set "shortcut_generator_script=generate_shortcuts.py"
set "terminal_title=Generating Shortcuts"
set "install_backend_script=install_backend_python.bat"

:: ===========================
:: code execution

:: change title
title %terminal_title%

:: install backend python if not already installed. This will also install pip and the packages
if not exist "%python_exe%" (
    :: error handling and exit is inside
    call "%install_backend_script%"
) 

:: generate shortcuts
"%python_exe%" "%shortcut_generator_script%"
set "exit_code=%ERRORLEVEL%"

:: exit if success
if "%exit_code%"=="0" (
    exit /b 0
)

:: print and confirm to close on failure
echo [Error] Shortcut generation failed. Aborting. Press any key to exit.
pause > nul
exit /b %exit_code%
