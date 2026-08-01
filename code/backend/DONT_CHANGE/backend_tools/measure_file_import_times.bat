:: Description: Measures selected backend-module import times directly.
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
set "target_script=..\scripts\backend_tools\measure_file_import_times.py"
set "code_dir=..\.."
set "modules=backend.DONT_CHANGE.settings.backend_settings backend.DONT_CHANGE.scripts.common_code"

:: ===========================
:: code execution

call "%ensure_backend_python_script%"
if errorlevel 1 exit /b 1
"%python_exe%" "%target_script%" 10 "%code_dir%" %modules% %*
exit /b %ERRORLEVEL%
