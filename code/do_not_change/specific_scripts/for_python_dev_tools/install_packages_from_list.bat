:: ========================
:: --- Code Description ---
:: ========================

:: This batch file installs packages from a list of packages provided as an argument with "pip install -r".


:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands &  make variables local & enable needed features:
@echo off & setlocal EnableDelayedExpansion

:: define local variables (with relative paths being relative to this file)
set "environment_activator_path=..\create_and_or_activate_python_env.bat"

:: get current file path for relative path variables:
set "current_file_path=%~dp0"

:: handle args
SET "packages_list_path=%~1"
IF "%packages_list_path%"=="" (
	echo [Error 1] No packages list path provided as first argument. Aborting. Press any key to exit.
	pause > nul
	exit 1
)
:: make packages_list_path to absolute path:
CALL :make_absolute_path_if_relative "%packages_list_path%"
SET "packages_list_path=%OUTPUT%"

:: check if files exist
if NOT exist "%packages_list_path%" (
	echo [Error 2] "%packages_list_path%" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 2
)

:: goto folder of this file:
pushd "%current_file_path%"
:: check if environment activator exists:
if NOT exist "%environment_activator_path%" (
	echo [Error 3] "%environment_activator_path%" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 3
)
:: activate or create & activate virtual Python environment:
call "%environment_activator_path%"
:: install packages from file or warn if it does not exist and abort:
REM can't use pip directly here because pip is implemented in portable venv as batch and does not return (alternatively works if called with "call"):
python -m pip install -r "%packages_list_path%"  --upgrade --disable-pip-version-check --no-cache-dir 
if "!ERRORLEVEL!" neq "0" ( 
	echo [Error 5] Failed to install packages from file. Press any key to exit.
	popd
	pause > nul
	exit 5 
)
:: return to original folder:
popd

:: exit program and close calling program
echo.
echo Installation completed if no errors above. Press any key to exit.
pause > nul
exit 0

:: ====================
:: ==== Functions: ====
:: ====================

::::::::::::::::::::::::::::::::::::::::::::::::
:: function that makes relative path (relative to current working directory) to :: absolute if not already. Works for empty path (relative) path:
:: Usage:
::    call :make_absolute_path_if_relative "%some_path%"
::    set "abs_path=%output%"
::::::::::::::::::::::::::::::::::::::::::::::::
:make_absolute_path_if_relative
    if "%~1"=="" (
        set "OUTPUT=%cd%"
    ) else (
	    set "OUTPUT=%~f1"
    )
goto :EOF
:: =================================================