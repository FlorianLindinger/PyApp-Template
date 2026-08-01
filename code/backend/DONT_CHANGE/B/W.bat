:: Description: Starts the application in a terminal.
::
:: ===========================

:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: ===========================
:: settings

:: move to folder of this file:
cd /d "%~dp0"

:: ===========================
:: local variables

set "app_id=%~1"
set "launch_mode=terminal"
set "ensure_backend_python_script=helper_scripts\ensure_backend_python.bat"
set "target_script=..\scripts\shortcut_targets\start_program.py"

:: ===========================
:: code execution

:: install backend Python if needed and receive its path in python_exe:
call "%ensure_backend_python_script%"
:: exit on failure (print and confirm close handled in child):
if not "%ERRORLEVEL%"=="0" (
    exit 1
)

:: run python script and forward all args:
"%python_exe%" "%target_script%" "%app_id%" "%launch_mode%"
set "exit_code=%ERRORLEVEL%"

:: exit if success:
if "%exit_code%"=="0" (
    exit 0
)

:: print and confirm to close on failure:
echo [Error] Python script failed with exit code %exit_code%. Press any key to exit.
pause > nul
exit %exit_code%
::
:: ===========================
