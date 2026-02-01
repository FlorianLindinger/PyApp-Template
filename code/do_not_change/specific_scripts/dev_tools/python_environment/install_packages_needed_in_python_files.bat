:: ========================
:: --- Code Description ---
:: ========================





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
set "folder_to_search_for_stuff_needing_packages=..\..\..\..\"
set "python_file_requirements_path=..\..\..\..\py_env\auto_detected_package_requirements.txt"
set "python_environment_folder_path=..\..\..\..\py_env"
set "do_not_change_folder_path=..\..\..\..\do_not_change"
set "dev_tools_folder_path=..\..\..\..\dev_tools"

if NOT exist "%environment_activator_path%" (
	echo [Error 1] "%environment_activator_path%" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 1
)

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
python -m venv "%tmp_venv_path%"
call "%tmp_venv_path%/Scripts/activate.bat"   
pip install pipreqs --disable-pip-version-check > nul

:: get needed packages:
pipreqs "%folder_to_search_for_stuff_needing_packages%" --force --savepath "%python_file_requirements_path%" --ignore "%python_environment_folder_path%" --ignore "%do_not_change_folder_path%" --ignore "%dev_tools_folder_path%" --encoding utf-8 --no-follow-links 

:: deactivate temp environment and delete:
deactivate 
:: carefull with name because it will delete everything:
rmdir /s /q "%tmp_venv_path%"

:: reactivate python environment:
call "%environment_activator_path%"
if %errorlevel% neq 0 (
	echo.
	echo [Error 3] Failed to activate or create the Python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit 3
)

:: install list of needed packages
REM can't use pip directly here because pip is implemented in portable venv as batch and does not return (alternatively works if called with "call"):
python -m pip install -r "%python_file_requirements_path%" --upgrade --disable-pip-version-check --no-cache-dir

:: print final message and exit after key press
echo.
echo.
echo.
echo Everything needed in the python files should be installed now if no errors are above. Press any key to exit.
pause > nul
exit 0