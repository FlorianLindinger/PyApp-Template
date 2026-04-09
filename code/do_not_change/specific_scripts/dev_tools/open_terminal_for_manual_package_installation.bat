:: ========================
:: --- Code Description ---
:: ========================

:: This batch file opens a terminal with the Python environment activated for manual package installation.

:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands &  make variables local:
@echo off & setlocal

:: define local variables (with relative paths being relative to this file)
set "environment_activator_path=..\..\create_and_or_activate_python_env.bat"
set "python_environment_path=..\..\..\..\py_env\virt_env"

:: get current file path for relative path variables:
set "current_file_path=%~dp0"
:: goto folder of this file:
pushd "%current_file_path%"

:: check if environment activator exists:
if not exist "%environment_activator_path%" (
	echo [Error 1] "%environment_activator_path%" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 1
)

:: ======================
:: --- Code Execution ---
:: ======================

:: activate or create & activate virtual Python environment:
call "%environment_activator_path%"
if %errorlevel% neq 0 (
	echo.
	echo [Error 1] Failed to activate or create the Python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit 1
)

:: upgrade pip
REM can't use pip directly here because pip is implemented in portable venv as batch and does not return (alternatively works if called with "call"):
call python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [Warning] pip upgrade failed.
) else (
	cls
)

:: check if environment activator file exists:
if not exist "%python_environment_path%\Scripts\activate.bat" (
	echo [Error 1] "%python_environment_path%\Scripts\activate.bat" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 1
)

:: move to folder of python environment for visual indicatedtion in terminal where env is:
cd /d "%python_environment_path%"

:: print how to install:
echo Write 'pip install {package name}' to install a package in the local environment:
echo.

:: start terminal in old terminal with environment:
start /b /wait call "Scripts\activate.bat"

:: print warning because this code should not be reached:
echo.
echo Error (See above)! Press any key to exit
pause > nul 
exit 2

