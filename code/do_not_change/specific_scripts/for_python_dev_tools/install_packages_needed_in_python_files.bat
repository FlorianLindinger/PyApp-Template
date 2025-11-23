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
set "environment_activator_path=install_and_or_activate_python_env.bat"
set "folder_of_python_files_to_search=..\..\"
set "python_file_requirements_path=..\..\py_env\python_file_requirements.txt"
set "python_environment_path=..\..\py_env"
set "tmp_env_path=tmp_env_for_install_package_from_files"

:: ======================
:: --- Code Execution ---
:: ======================

:: activate (or create & activate) python environment:
call "%environment_activator_path%"

python -m venv "%tmp_env_path%"
"%tmp_env_path%/Scripts/activate"   
pip install pipreqs --disable-pip-version-check > nul
pipreqs "%folder_of_python_files_to_search%" --force --savepath "%python_file_requirements_path%" --ignore "%python_environment_path%"?
deactivate
:: carefull with name because it will delete everything:
rmdir /s /q "%tmp_env_path%"

:: reactivate python environment:
call "%environment_activator_path%"

:: install list of needed packages
pip install --disable-pip-version-check --upgrade -r "%python_file_requirements_path%"

:: print final message and exit after key press
echo.
echo.
echo.
echo Everything needed in the python files should be installed now if no errors are above. Press any key to exit.
pause > nul
exit 0