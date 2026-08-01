:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: move to folder of this file:
cd /d "%~dp0"

:: ===========================
:: local variables

set "ensure_backend_python_script=..\helper_scripts\ensure_backend_python.bat"
set "target_script=..\..\scripts\dev_tools\scripts\set_default_packages -names.py"

:: ===========================
:: code execution

:: install backend Python if needed and receive its path in python_exe:
call "%ensure_backend_python_script%"
:: exit on failure (print and confirm close handled in child):
if not "%ERRORLEVEL%"=="0" (
    exit 1
)

:: run python script and forward all args:
"%python_exe%" "%target_script%" %*
set "exit_code=%ERRORLEVEL%"

:: exit if success:
if "%exit_code%"=="0" (
    exit 0
)

:: print and confirm to close on failure:
echo [Error] Python script failed with exit code %exit_code%. Press any key to exit.
pause > nul
exit %exit_code%
