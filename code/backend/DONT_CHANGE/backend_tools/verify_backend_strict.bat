:: Description: Runs strict backend verification without modifying source files.
@echo off
setlocal
cd /d "%~dp0"

set "ensure_backend_python_script=..\B\helper_scripts\ensure_backend_python.bat"
set "target_script=..\scripts\backend_tools\verify_backend.py"

call "%ensure_backend_python_script%"
if errorlevel 1 exit /b 1
:run
cls
"%python_exe%" "%target_script%" strict %*
set "exit_code=%ERRORLEVEL%"
if not "%exit_code%"=="0" echo [Error] Backend strict verification failed with exit code %exit_code%.
set /p "_rescan=[Input] Press Enter to rescan: "
goto :run
