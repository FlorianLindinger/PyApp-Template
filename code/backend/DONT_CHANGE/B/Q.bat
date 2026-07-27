<<<<<<< HEAD
@echo off
setlocal

:: =================================

set "launcher_dir=%~dp0"
set "python_exe=%launcher_dir%..\backend_python\python.exe"
set "backend_script=%launcher_dir%..\scripts\stop_program.py"

:: =================================

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
=======
:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: move to folder of this file:
cd /d "%~dp0"

:: ===========================
:: local variables

set "ensure_backend_python_script=..\scripts\setup\ensure_backend_python.bat"
set "target_script=..\scripts\shortcut_targets_via_batch\stop_program.py"

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
>>>>>>> f82a4acb989934bff49b56bdc7577c626a3fa40c
