:: Description: Runs basic verification for main.py.
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

set "ensure_backend_python_script=..\helper_scripts\ensure_backend_python.bat"
set "target_script=..\..\scripts\dev_tools\verify_main_py.py"

:: ===========================
:: code execution

:: install backend Python if needed and receive its path in python_exe:
call "%ensure_backend_python_script%"
:: exit on failure (print and confirm close handled in child):
if not "%ERRORLEVEL%"=="0" (
    exit 1
)

:run
cls
:: run python script and forward all args:
"%python_exe%" "%target_script%" basic %*
set "exit_code=%ERRORLEVEL%"

if not "%exit_code%"=="0" echo [Error] Python script failed with exit code %exit_code%.
set /p "_rescan=[Input] Press Enter to rescan: "
goto :run
::
:: ===========================
