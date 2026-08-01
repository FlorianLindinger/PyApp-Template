:: disable printing of commands:
@echo off
setlocal
cd /d "%~dp0"

:: ===========================
:: local variables

set "ensure_backend_python_script=..\helper_scripts\ensure_backend_python.bat"
set "target_script=..\..\scripts\backend_tools\verify_backend.py"

:: ===========================
:: code execution

:: install backend Python if needed and receive its path in python_exe:
call "%ensure_backend_python_script%"
if not "%ERRORLEVEL%"=="0" exit /b 1

"%python_exe%" "%target_script%" strict %*
set "exit_code=%ERRORLEVEL%"
if "%exit_code%"=="0" exit /b 0

echo [Error] Backend verification failed with exit code %exit_code%. Press any key to exit.
pause > nul
exit /b %exit_code%
