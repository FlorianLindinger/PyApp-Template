:: Description: Regenerates the multi-resolution shortcut icons.
::
:: ===========================

:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: ===========================
:: settings

:: move to folder of this file:
cd /d "%~dp0"

:: ===========================
:: local variables

set "ensure_backend_python_script=..\helper_scripts\ensure_backend_python.bat"
set "target_script=..\..\scripts\icon\generate_icons.py"

:: ===========================
:: code execution

call "%ensure_backend_python_script%"
if not "%ERRORLEVEL%"=="0" exit /b 1

"%python_exe%" "%target_script%" %*
set "exit_code=%ERRORLEVEL%"
if "%exit_code%"=="0" exit /b 0

echo [Error] Icon generation failed. Press any key to exit.
pause > nul
exit /b %exit_code%
::
:: ===========================
