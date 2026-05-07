@echo off
setlocal

set "launcher_dir=%~dp0"
set "python_exe=%launcher_dir%P\P.exe"
set "backend_script=%launcher_dir%specific_scripts\open_settings.py"

if not exist "%python_exe%" (
    echo [Error] Backend Python not found:
    echo "%python_exe%"
    pause
    exit /b 1
)

"%python_exe%" "%backend_script%"
set "exit_code=%ERRORLEVEL%"

if not "%exit_code%"=="0" (
    echo.
    echo ====================
    echo [Error] Launcher failed with code: %exit_code%
    echo --------------------
    pause
)

exit /b %exit_code%
