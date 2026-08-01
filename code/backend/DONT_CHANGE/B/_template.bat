:: {ADD DOCSTRING DESCRIPTION HERE
::
:: This template is meant to be applied to all batch files in the parent folder of this file, except for:
:: - this file itself
:: - helper_scripts/generic_helpers/*.bat
:: and batch files in ../backend_tools.
:: 
:: }

:: ===========================

:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: ===========================
:: settings

:: ===========================
:: local variables (use "%~dp0" to indicate in a path the folder of this file, e.g. "%~dp0helper_scripts\ensure_backend_python.bat")

set "ensure_backend_python_script={RELATIVE PATH TO helper_scripts\ensure_backend_python.bat}"
set "target_script={RELATIVE PATH TO TARGET SCRIPT}.py"

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
