:: ========================
:: --- Code Description ---
:: ========================

todo:
check if existance checks needed
max_repeats
checl what abs PATH i need and if i dont want to run all code always
maybe remove generate requriements.txt?
maybe lease install packages from file?

add back install packages batch as utility for py app with correct paths

use goto:s or functions
cathc errors of called scripts

test if python verison "" works

test startup time before python
maybe make batch file that prints runtime of call

##################
start code
white error and num_repeats  < max_repeats:
    old_time = get time
	if repeate_main
	   start code
	else:
	   start fail code
    if get_toime < old_time + 1 sek:
	   sleep 1 sek
##################

print totla report of if crhases of waht happended

##################

:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands and make definitions local
@ECHO OFF & SETLOCAL

:: define local variables (with relative paths being relative to this file)
SET "settings_path=..\non-user_settings.ini"

set "python_version_checker_path=utilities\python_environment\check_if_python_version_matches.bat"
set "portable_python_installer_path=utilities\python_environment\create_portable_python.bat"
set "portable_venv_creator_path=utilities\python_environment\create_portable_venv.bat"
set "requirements_generator_path=utilities\python_environment\generate_requirements.txt_no_version.bat"

set "python_folder_folder_path=..\python_environment"
set "python_folder_path=%python_folder_folder_path%\portable_python"
set "python_exe_path=%python_folder_path%\python.exe"
set "env_activator_path=%python_folder_folder_path%\virtual_environment\activate.bat"
set "default_packages_list=%python_folder_folder_path%\default_python_packages.txt"

:: move to folder of this file (needed for relative paths)
:: current_file_path variable needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path=%~dp0"
CD /D "%current_file_path%"

:: make paths absolute if not
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%settings_path%" 
SET "settings_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%python_version_checker_path%" 
SET "python_version_checker_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%portable_python_installer_path%" 
SET "portable_python_installer_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%portable_venv_creator_path%" 
SET "portable_venv_creator_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%requirements_generator_path%" 
SET "requirements_generator_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%python_folder_folder_path%" 
SET "python_folder_folder_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%env_activator_path%" 
SET "env_activator_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%python_exe_path%" 
SET "python_exe_path=%OUTPUT%"

:: check if files exist
IF NOT exist "%settings_path%" (
	echo: [Error] "%settings_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)
IF NOT exist "%python_version_checker_path%" (
	echo: [Error] "%python_version_checker_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)
IF NOT exist "%portable_python_installer_path%" (
	echo: [Error] "%portable_python_installer_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)
IF NOT exist "%portable_venv_creator_path%" (
	echo: [Error] "%portable_venv_creator_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)

:: import settings from %settings_path%:
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( SET "%%A=%%B" )

:: check if defined in settings_path
if "%icon_path%"=="" (
	echo: [Error] icon_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)
if "%python_code_path%"=="" (
	echo: [Error] python_code_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)

:: convert the path settings that are relative to settings file (at %settings_path%%) to absolute paths:
FOR %%I IN ("%settings_path%") DO SET "settings_dir=%%~dpI"
CD /D "%settings_dir%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%icon_path%" 
SET "icon_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%python_code_path%" 
SET "python_code_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%after_python_crash_code_path%" 
SET "after_python_crash_code_path=%OUTPUT%"
CD /D "%current_file_path%"

:: get python code paths directoriers:
FOR %%F IN ("%python_code_path%") DO (
    SET "python_code_dir=%%~dpF"
)
FOR %%F IN ("%after_python_crash_code_path%") DO (
    SET "crash_python_code_dir=%%~dpF"
)

:: ======================
:: --- Code Execution ---
:: ======================

:: change terminal title:
TITLE %program_name%

:: change terminal colors (for starting lines):
COLOR %terminal_bg_color%%terminal_text_color%

:: change terminal icon:
change_icon "%program_name%" "%icon_path%"

:: get name of current localization language needed for cmd.exe that presumably runs this script
for /f "tokens=2,*" %%A in ('reg query "HKCU\Control Panel\Desktop" /v PreferredUILanguages 2^>nul') do (
	for %%L in (%%B) do (
	set "UI_LANG=%%L"
	goto :done
	)
)
:done
REM check if successful
if "%UI_LANG%"=="" (
	ECHO: [Error] Could not determine system language. Aborting. Press any key to exit.
	PAUSE >NUL 
	EXIT /B 2
)

:: create localization language folder if missing
if not exist "CMD_exes\%UI_LANG%\" (
	mkdir "CMD_exes\%UI_LANG%"
	robocopy "CMD_exes\mui_files" "CMD_exes\%UI_LANG%" /E /R:0 /W:0 /NFL /NDL /NJH /NJS /NP
)
REM check if successful
if errorlevel 8 (
	ECHO: [Error] Copy Windows language files. Aborting. Press any key to exit.
	PAUSE >NUL 
	EXIT /B 3
)

::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: activate or create & activate python environment:

if not exist "%python_exe_path%" ( &:: python not existing case
	rem install python:
    call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%"
	if "%ERRORLEVEL%" neq 0 ( exit /b 4 ) &:: failed to install python. Error print and wait already in call
	rem install virtual env:
	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
    if "%ERRORLEVEL%" neq 0 ( exit /b 5 ) &:: failed to install venv. Error print and wait already in call
	rem activate env:
    call "%env_activator_path%"
	rem install packages:
    if not exist "%default_packages_list%" ( &:: python packages list existing case
        call :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%default_packages_list%"
		set "default_packages_list=%OUTPUT%"
        echo.
	    echo [Warning] List of default Python packages ("%default_packages_list%"^) not found. Skipping installation.
	    echo.
		goto end_of_activation
	) else ( &:: python packages list not existing case
    	echo.
    	echo [Info] Installing packages:
    	echo.
    	pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
    	echo.
    	echo [Info] Finished installing packages
        echo.
    	goto end_of_activation
	)
) else ( &:: python existing case
	rem check python version matches setting:
	CALL "%python_version_checker_path%" "%python_version%" "%python_exe_path%"
	if "%errorlevel%" neq 0 ( exit /b 6 ) &:: failed to determine python version. Error print and wait already in call
	if "%OUTPUT%"=="1" ( &:: python version matching case
	   if exist "%env_activator_path%" ( &:: env existing case
            rem activate env:
            call "%env_activator_path%"
			goto end_of_activation
	   ) else ( &:: env not existing case
        	rem install virtual env:
        	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
            if "%ERRORLEVEL%" neq 0 ( exit /b 7 ) &:: failed to install venv. Error print and wait already in call
        	rem activate env:
            call "%env_activator_path%"
        	rem install packages:
            if not exist "%default_packages_list%" ( &:: python packages list existing case
                call :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%default_packages_list%"
        		set "default_packages_list=%OUTPUT%"
                echo.
        	    echo [Warning] List of default Python packages ("%default_packages_list%"^) not found. Skipping installation.
        	    echo.
        		goto end_of_activation
        	) else ( &:: python packages list not existing case
            	echo.
            	echo [Info] Installing packages:
            	echo.
            	pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
            	echo.
            	echo [Info] Finished installing packages
                echo.
            	goto end_of_activation
        	)
	   )  &:: end of env not existing case
	) else ( &:: python version not matching case
	   if exist "%env_activator_path%" ( &:: env existing case
	        rem ask user if he wants to recreate python and venv with current packages
            echo.
            echo: [Warning] Installed Python version is not compatible with the version specified in "%settings_path%" (%python_version%^).
		    echo: Do you want to locally for this program reinstall Python + virtual environment + current packages OR stay with current setup?
		    call :prompt_user
            if "%OUTPUT%"=="1" ( &:: user: yes case
			    rem activate to get current packages:
                call "%env_activator_path%"
                rem get current packages:
                call "%requirements_generator_path%" "%python_folder_folder_path%\tmp_requirement.txt"
			    if "%ERRORLEVEL%" neq 0 ( exit /b 8 ) &:: failed to generate package list. Error print and wait already in call
                rem reinstall python:
                call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%"
			    if "%ERRORLEVEL%" neq 0 ( exit /b 9 ) &:: failed to reinstall python. Error print and wait already in call
			    rem reinstall virtual env:
			    call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
                if "%ERRORLEVEL%" neq 0 ( exit /b 10 ) &:: failed to reinstall venv. Error print and wait already in call
			    rem activate to reinstall packages:
                call "%env_activator_path%"
			    rem reinstall packages:
                if not exist "%default_packages_list%" ( &:: python packages list existing case
                    call :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%default_packages_list%"
        		    set "default_packages_list=%OUTPUT%"
                    echo.
        	        echo [Warning] List of default Python packages ("%default_packages_list%"^) not found. Skipping installation.
        	        echo.
        		    goto end_of_activation
        	    ) else ( &:: python packages list not existing case
            	    echo.
            	    echo [Info] Installing packages:
            	    echo.
            	    pip install -r "%python_folder_folder_path%\tmp_requirement.txt" --disable-pip-version-check --upgrade --no-cache-dir 
            	    echo.
            	    echo [Info] Finished installing packages
                    echo.
            	    goto end_of_activation
        	    )
		    ) else (  &:: user: no case
			    rem activate:
                call "%env_activator_path%"
			    goto end_of_activation
		    )
	   ) else ( &:: env not existing case. User does not get asked for python reinstall since either way no venv lost
        	rem reinstall python:
            call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%"
        	if "%ERRORLEVEL%" neq 0 ( exit /b 11 ) &:: failed to install python. Error print and wait already in call
        	rem install virtual env:
        	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
            if "%ERRORLEVEL%" neq 0 ( exit /b 12 ) &:: failed to install venv. Error print and wait already in call
        	rem activate env:
            call "%env_activator_path%"
        	rem install packages:
            if not exist "%default_packages_list%" (  &:: python packages list existing case
                call :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%default_packages_list%"
        		set "default_packages_list=%OUTPUT%"
                echo.
        	    echo [Warning] List of default Python packages ("%default_packages_list%"^) not found. Skipping installation.
        	    echo.
        		goto end_of_activation
        	) else (  &:: python packages list not existing case
            	echo.
            	echo [Info] Installing packages:
            	echo.
            	pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
            	echo.
            	echo [Info] Finished installing packages
                echo.
            	goto end_of_activation
        	)
	   ) &:: end of env not existing case
    ) &:: end of python version not matching case
) &:: end of python existing case

:end_of_activation
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

:: go to directory of main python code and execute it and return to folder of this file:
CD /D "%python_code_dir%"
python "%python_code_path%"
CD /D "%current_file_path%"

:: %ERRORLEVEL% is what the last python execution gives out in sys.exit(errorlevel). 
:: Errorlevel 1 (default for python crash) will run main_code.py or after_python_crash_code.py (depending on parameter restart_main_code_on_crash in non-user_settings.ini). Errorlevel -1 will exit the terminal. Any other value will pause the terminal until user presses a button (unless this script is called with any argument):
IF %ERRORLEVEL% EQU 1 (
	SET "original_python_crashed=1"
	CALL :handle_python_crash
)
:: Does not pause if python returns an errorlevel -1 with sys.exit(-1) in python:
IF %ERRORLEVEL% EQU -1 (
	EXIT /B 0
)

:: print final report message:
ECHO:
IF "%original_python_crashed%"=="1" (
	IF "%python_crash_handler_crashed%"=="1" (
		ECHO: ========================================================
		ECHO: Finished all python execution.
		ECHO: The main python code crashed and the python function for
		ECHO: handling crashes crashed at least once before finishing 
		ECHO: successfully now (see above^)
		ECHO: ========================================================
	) ELSE (
		ECHO: ======================================================
		ECHO: Finished all python execution.
		ECHO: The main python code crashed but the python function
		ECHO: for handling crashes finished successfully (see above^)
		ECHO: ======================================================
	)
) ELSE (
	ECHO: =================================
	ECHO: Python code finished successfully
	ECHO: =================================
)
ECHO:

:: wait for any key and exit
ECHO: Finished code execution. Press any key to exit
PAUSE >NUL 
EXIT /B 0

:: ====================
:: ==== Functions: ====
:: ====================

::::::::::::::::::::::::::::::::::::::::::::::
:: function to handle python crashes:
::::::::::::::::::::::::::::::::::::::::::::::
:handle_python_crash
ECHO:
ECHO: ===================================================
ECHO: WARNING: Python returned 1, which indicates a crash
ECHO: ===================================================
ECHO:
IF %restart_main_code_on_crash% EQU 0 ( @REM  run after_python_crash_code.py (again)
	IF EXIST "%after_python_crash_code_path%" (
		ECHO:
		ECHO: ===============================================
		ECHO: Running python code intended for after crashes:
		ECHO: ===============================================
		ECHO:
		:: go to directory of python code and execute it and return to folder of this file:	
		CD /D "%python_code_dir%"
		python "%python_code_path%"
		CD /D "%current_file_path%"
		ECHO:
	:: exit function if after_python_crash_code does not exist
	) ELSE (
		EXIT /B 0 &@REM exit function with errorcode 0
	)
)	ELSE (  @REM run main_code.py again
	ECHO:
	ECHO: ================================================
	ECHO: Running main python code again after it crashed:
	ECHO: ================================================
	ECHO:
	:: go to directory of python code and execute it and return to folder of this file:
	CD /D "%crash_python_code_dir%"
	python "%after_python_crash_code_path%" "crashed" &@REM argument "crashed" indicated to the python code that it is a repeat call after a crash and can be checked for with sys.argv[-1]=="crashed"
	CD /D "%current_file_path%"
	ECHO:
)
IF %ERRORLEVEL% EQU 1 ( @REM could be infinitely recursive
	SET python_crash_handler_crashed=1
	CALL :handle_python_crash
)
EXIT /B 0 &@REM exit function with errorcode 0
:: =================================================
:: =================================================


::::::::::::::::::::::::::::::::::::::::::::::::
:: function that makes relative path (relative to current working directory) to :: absolute if not already. Works for empty path (relative) path:
:: Usage:
::    call :make_absolute_path_if_relative "%some_path%"
::    set "abs_path=%output%"
::::::::::::::::::::::::::::::::::::::::::::::::
:make_absolute_path_if_relative
    if "%~1"=="" (
        set "OUTPUT=%CD%"
    ) else (
	    set "OUTPUT=%~f1"
    )
goto :EOF
:: =================================================
:: =================================================


::::::::::::::::::::::::::::::::::::::::::::::::
:: function that prompts user with "Enter y/n for Yes/No" and sets OUTPUT=1 for y and OUTPUT=0 for n.
::::::::::::::::::::::::::::::::::::::::::::::::
:prompt_user
	CHOICE /c YN /m Delete? Enter y/n for Yes/No
	IF %ERRORLEVEL%==1 (
		set "OUTPUT=1"
	) else (
		set "OUTPUT=0"
	)
GOTO :EOF
:: =================================================
:: =================================================