@echo off
setlocal

set "launcher_dir=%~dp0"
set "python_exe=%launcher_dir%backend_python\python.exe"
set "backend_script=%launcher_dir%scripts\start_program.py"
set "app_id=%~1"
set "launch_mode=terminal_emulator"

if not "%PYAPP_LAUNCHER_MINIMIZED%"=="1" (
    findstr /R /C:"^[ ]*start_minimized[ ]*=[ ]*True" "%launcher_dir%..\developer_settings.py" >nul 2>nul
    if not errorlevel 1 (
        set "PYAPP_LAUNCHER_MINIMIZED=1"
        start "" /min "%COMSPEC%" /d /c call "%~f0" %*
        exit
    )
)

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
