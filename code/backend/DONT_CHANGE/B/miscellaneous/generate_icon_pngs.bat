:: Create editable placeholder PNGs for the shortcut icons.
@echo off
setlocal
cd /d "%~dp0"

set "ensure_backend_python_script=..\helper_scripts\ensure_backend_python.bat"
set "target_script=..\..\scripts\icon\generate_PNGs_to_be_replaced.py"

call "%ensure_backend_python_script%"
if not "%ERRORLEVEL%"=="0" exit /b 1

"%python_exe%" "%target_script%" %*
set "exit_code=%ERRORLEVEL%"
if "%exit_code%"=="0" exit /b 0

echo [Error] PNG placeholder generation failed. Press any key to exit.
pause > nul
exit /b %exit_code%
