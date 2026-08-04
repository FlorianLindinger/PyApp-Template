:: Description: Applies Ruff fixes, then runs default backend verification.
::
:: ===========================

:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: move to folder of this file:
cd /d "%~dp0"

:: ===========================
:: local variables

set "ensure_backend_python_script=..\B\helper_scripts\ensure_backend_python.bat"
set "target_script=..\scripts\backend_tools\verify_backend.py"

:: ===========================
:: code execution

call "%ensure_backend_python_script%"
if errorlevel 1 exit /b 1
:run
cls
"%python_exe%" "%target_script%" default --fix %* %run_options%
set "exit_code=%ERRORLEVEL%"
if not "%exit_code%"=="0" echo [Error] Backend default verification failed with exit code %exit_code%.
set "run_options="
set /p "_rescan=[Input] Press Enter to rescan; type fix for safe fixes or unsafe for unsafe fixes: "
if /i "%_rescan%"=="fix" set "run_options=--fix"
if /i "%_rescan%"=="unsafe" set "run_options=--unsafe-fixes"
goto :run
