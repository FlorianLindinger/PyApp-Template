:: Regenerate the project's multi-resolution shortcut icons.
@echo off
setlocal
cd /d "%~dp0"

set "ensure_backend_python_script=..\helper_scripts\ensure_backend_python.bat"
set "target_script=..\..\icon_related\generate_icons.py"

call "%ensure_backend_python_script%"
if not "%ERRORLEVEL%"=="0" exit /b 1

"%python_exe%" "%target_script%" %*
set "exit_code=%ERRORLEVEL%"
if "%exit_code%"=="0" exit /b 0

echo [Error] Icon generation failed. Press any key to exit.
pause > nul
exit /b %exit_code%
