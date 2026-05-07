@echo off
setlocal

set "launcher_dir=%~dp0"
set "python_exe=%launcher_dir%P\P.exe"
set "backend_script=%launcher_dir%specific_scripts\start_program.py"
set "app_id=%~1"
set "launch_mode=browser"

if not exist "%python_exe%" (
    echo [Error] Backend Python not found:
    echo "%python_exe%"
    pause
    exit /b 1
)

"%python_exe%" "%backend_script%" "%app_id%" "%launch_mode%"
set "exit_code=%ERRORLEVEL%"

if not "%exit_code%"=="0" (
    echo.
    echo ====================
    echo [Error] Launcher failed with code: %exit_code%
    echo --------------------
    pause
)

exit /b %exit_code%
