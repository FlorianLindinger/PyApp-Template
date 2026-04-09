:: ========================
:: --- Code Description ---
:: ========================

use determine_requirements.txt.bat to determine needed packages from python files and install them in the python environment.
look at todo list



:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands &  make variables local:
@echo off & setlocal

:: move to folder of this file (needed for relative path shortcuts)
:: current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
set "current_file_path=%~dp0"
cd /d "%current_file_path%"

:: define local variables (with relative paths being relative to this file)
REM carefull with path of tmp_venv_path because it deletes this folder afterwards
set "tmp_venv_path=%temp%\tmp_venv_for_install_package_from_files"
set "environment_activator_path=..\..\create_and_or_activate_python_env.bat"
REM leave out backslashes at end
set "folder_to_search_for_stuff_needing_packages=..\..\..\.."
set "python_file_requirements_path=..\..\..\..\py_env\auto_detected_package_requirements.txt"
set "python_environment_folder_path=..\..\..\..\py_env"
set "do_not_change_folder_path=..\..\..\..\do_not_change"
set "dev_tools_folder_path=..\..\..\..\dev_tools"

if NOT exist "%environment_activator_path%" (
	echo [Error 1] "%environment_activator_path%" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 1
)

call :set_abs_path "%folder_to_search_for_stuff_needing_packages%" "folder_to_search_for_stuff_needing_packages"
call :set_abs_path "%python_file_requirements_path%" "python_file_requirements_path"
call :set_abs_path "%python_environment_folder_path%" "python_environment_folder_path"
call :set_abs_path "%do_not_change_folder_path%" "do_not_change_folder_path"
call :set_abs_path "%dev_tools_folder_path%" "dev_tools_folder_path"

:: ======================
:: --- Code Execution ---
:: ======================

:: activate (or create & activate) python environment:
call "%environment_activator_path%"
if %errorlevel% neq 0 (
	echo.
	echo [Error 2] Failed to activate or create the Python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit 2
)

:: create temp environment and install pipreqs:
call python -m venv "%tmp_venv_path%"
if %errorlevel% neq 0 (
	echo.
	echo [Error 3] Failed to create temporary python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit 3
)
call "%tmp_venv_path%/Scripts/activate.bat"   
if %errorlevel% neq 0 (
	echo.
	echo [Error 4] Failed to activate temporary python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit 4
)
pip install pipreqs --disable-pip-version-check > nul
if %errorlevel% neq 0 (
	echo.
	echo [Error 5] Failed to install pipreqs in temporary python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit 5
)

:: print start message:
echo .
echo ==============================================
echo Scanning python files for needed packages in "%folder_to_search_for_stuff_needing_packages%" 
echo ==============================================
echo.

:: get needed packages:
pipreqs --force --savepath "%python_file_requirements_path%" --ignore "%python_environment_folder_path%,%do_not_change_folder_path%,%dev_tools_folder_path%" --encoding utf-8 --no-follow-links "%folder_to_search_for_stuff_needing_packages%" 

if %errorlevel% neq 0 (
	echo.
	echo [Error 6] Failed to get needed packages from python files (see above^). Aborting. Press any key to exit.
	pause > nul
	exit 6
)

:: print found packages:
echo.
echo ==============================================
echo Found the following packages needed in the python files:
echo ==============================================
type "%python_file_requirements_path%"
echo ==============================================
echo.

:: deactivate temp environment and delete:
call deactivate 

:: carefull with name because it will delete everything:
rmdir /s /q "%tmp_venv_path%"

:: reactivate python environment:
call "%environment_activator_path%"
if %errorlevel% neq 0 (
	echo.
	echo [Error 7] Failed to activate or create the Python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit 7
)

if %errorlevel% neq 0 (
	echo.
	echo [Error 8] Failed to activate the program Python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit 8
)

:: print message:
echo .
echo ==============================================
echo Installing needed packages
echo ==============================================
echo.

:: install list of needed packages
REM can't use pip directly here because pip is implemented in portable venv as batch and does not return (alternatively works if called with "call"):
call python -m pip install -r "%python_file_requirements_path%" --upgrade --disable-pip-version-check --no-cache-dir

if %errorlevel% neq 0 (
	echo.
	echo [Error 9] Failed to install needed packages from python files (see above^). Maybe try "reset_python_environment -InstallPackagesNeededInFiles.bat" in dev_tools\python_environment. Aborting. Press any key to exit.
	pause > nul
	exit 9
)

:: print final message and exit after key press
echo.
echo.
echo.
echo Everything needed in the python files should be installed now if no errors are above. Press any key to exit.
pause > nul
exit 0

:: ====================
:: ==== Functions: ====
:: ====================

::::::::::::::::::::::::::::::::::::::::::::::::
:: function that converts relative (to current working directory) path {arg1} to absolute and sets it to variable {arg2}. Works for empty path {arg1} which then sets the current working directory to variable {arg2}. Raises error if {arg2} is missing:
:: Usage:
::    call :set_abs_path "%some_path%" "some_path"
::::::::::::::::::::::::::::::::::::::::::::::::
:set_abs_path
    if "%~2"=="" (
        echo [Error] Second argument is missing for :set_abs_path function in "%~f0". (First argument was "%~1"^). 
        echo Aborting. Press any key to exit.
        pause > nul
        exit /b 1
    )
    if "%~1"=="" (
        set "%~2=%CD%"
    ) else (
	    set "%~2=%~f1"
    )
goto :EOF
:: =================================================