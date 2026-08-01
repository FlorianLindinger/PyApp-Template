:: Description: Runs strict backend verification directly.
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
"%python_exe%" "%target_script%" strict %*
exit /b %ERRORLEVEL%
