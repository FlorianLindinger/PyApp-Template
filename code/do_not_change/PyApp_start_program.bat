:: ========================
:: --- Code Description ---
:: ========================

@echo off

rem wait i need admin to copy from system32????

rem add nopause option for all scripts becaseu they would halt for no terminal usage. maybe does not matter eitehr way

rem current_file_path has \. maybe it matters. remove?

rem allow for space paths everywhere in app name and path

rem make a batch or c++ verison of change icon. Or add licenses for pyton veriosn. also to utilities

rem remove helper file for run_wihtout terminal. add delete with "; del" in powersehll part 

rem function call also changes ~dp0. so deliverate use only in beginning and set as variable. avoid move to local file. rather use explicitly this varialbe. add proper globla explanation that function call does that?

rem test faulthandler
rem change icon.exe weird? with no args? is usage being printed?

rem make change icon faster
rem is it possible to have pyqt5 window be same as launcher in taskbar

rem todo:
rem check if existance checks needed
rem max_repeats
rem checl what abs PATH i need and if i dont want to run all code always
rem maybe remove generate requriements.txt?
rem maybe lease install packages from file?

rem add back install packages batch as utility for py app with correct paths

rem use goto:s or functions
rem cathc errors of called scripts

rem make batch for generate non strict?

rem test startup time before python

rem somehow fix  that star tscitp closes delete file afterwards thing. want to keep utility tho. should work generally

rem ##################################



:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands &  make variables local & enable needed features
@echo off & setlocal EnableDelayedExpansion

:: define local variables (with relative paths being relative to this file)
set "settings_path=..\non-user_settings.ini"
set "cmd_exes_path=CMD_exes"

set "python_version_checker_path=utilities\python_environment\check_if_python_version_matches.bat"
set "portable_python_installer_path=utilities\python_environment\create_portable_python.bat"
set "portable_venv_creator_path=utilities\python_environment\create_portable_venv.bat"
set "requirements_generator_path=utilities\python_environment\generate_requirements.txt_no_version.bat"
set "icon_changer_path=utilities\change_icon.exe"

set "python_folder_folder_path=..\python_environment"
set "python_folder_path=%python_folder_folder_path%\portable_python"
set "python_exe_path=%python_folder_path%\python.exe"
set "env_activator_path=%python_folder_folder_path%\virtual_environment\activate.bat"
set "default_packages_list=%python_folder_folder_path%\default_python_packages.txt"

:: move to folder of this file (needed for relative paths)
:: current_file_path variable needed as workaround for nieche windows bug where this file gets called with quotation marks:
set "current_file_path=%~dp0"
cd /d "%current_file_path%"

:: make paths absolute if not
call :make_absolute_path_if_relative "%settings_path%" 
set "settings_path=%OUTPUT%"
call :make_absolute_path_if_relative "%python_version_checker_path%" 
set "python_version_checker_path=%OUTPUT%"
call :make_absolute_path_if_relative "%portable_python_installer_path%" 
set "portable_python_installer_path=%OUTPUT%"
call :make_absolute_path_if_relative "%portable_venv_creator_path%" 
set "portable_venv_creator_path=%OUTPUT%"
call :make_absolute_path_if_relative "%requirements_generator_path%" 
set "requirements_generator_path=%OUTPUT%"
call :make_absolute_path_if_relative "%python_folder_folder_path%" 
set "python_folder_folder_path=%OUTPUT%"
call :make_absolute_path_if_relative "%env_activator_path%" 
set "env_activator_path=%OUTPUT%"
call :make_absolute_path_if_relative "%python_exe_path%" 
set "python_exe_path=%OUTPUT%"

:: check if files exist
if NOT exist "%settings_path%" (
	echo [Error] "%settings_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 1
)
if NOT exist "%python_version_checker_path%" (
	echo [Error] "%python_version_checker_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 2
)
if NOT exist "%portable_python_installer_path%" (
	echo [Error] "%portable_python_installer_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 3
)
if NOT exist "%portable_venv_creator_path%" (
	echo [Error] "%portable_venv_creator_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 4
)

:: import settings from %settings_path%:
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( set "%%A=%%B" )

:: check if defined in settings_path
if "%icon_path%"=="" (
	echo [Error] icon_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit 5
)
if "%python_code_path%"=="" (
	echo [Error] python_code_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit 6
)

:: give default values if undefined
if "%restart_main_code_on_crash%"=="" (
	set "restart_main_code_on_crash=0"
)

:: convert the path settings that are relative to settings file (at %settings_path%%) to absolute paths:
FOR %%I IN ("%settings_path%") DO set "settings_dir=%%~dpI"
cd /d "%settings_dir%"
call :make_absolute_path_if_relative "%icon_path%" 
set "icon_path=%OUTPUT%"
call :make_absolute_path_if_relative "%python_code_path%" 
set "python_code_path=%OUTPUT%"
call :make_absolute_path_if_relative "%after_python_crash_code_path%" 
set "after_python_crash_code_path=%OUTPUT%"
cd /d "%current_file_path%"

:: get python code paths directoriers:
FOR %%F IN ("%python_code_path%") DO (
    set "python_code_dir=%%~dpF"
)
FOR %%F IN ("%after_python_crash_code_path%") DO (
    set "crash_python_code_dir=%%~dpF"
)

:: ======================
:: --- Code Execution ---
:: ======================

:: change terminal title:
TITLE %program_name%

:: change terminal colors (for starting lines):
COLOR %terminal_bg_color%%terminal_text_color%

:: change terminal icon via new terminal that does not delay code execution here (takes ~1s):
start "" /min "%icon_changer_path%" "%program_name%" "%icon_path%"

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
	echo [Error] Could not determine system language. Aborting. Press any key to exit.
	pause >nul 
	exit 7
)

:: create localization language folder if missing
if not exist "%cmd_exes_path%\%UI_LANG%\" (
	mkdir "%cmd_exes_path%\%UI_LANG%"
	robocopy "%cmd_exes_path%\mui_files" "%cmd_exes_path%\%UI_LANG%" /E /R:0 /W:0 /NFL /NDL /NJH /NJS /NP
)
REM check if successful
if errorlevel 8 (
	echo [Error] Copy Windows language files. Aborting. Press any key to exit.
	pause >nul 
	exit 8
)

::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: activate or create & activate python environment:

if not exist "%python_exe_path%" ( 
	REM python not existing case
	rem install python: "0" means no installation of Python docs
    call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%" "%install_tkinter%" "%install_tests%" "0"
	if "!ERRORLEVEL!" neq "0" ( exit 9 ) 
	rem above: failed to install python. Error print and wait already in call
	rem install virtual env:
	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
    if "!ERRORLEVEL!" neq "0" ( exit 10 ) 
	rem above: failed to install venv. Error print and wait already in call
	rem activate env:
    call "%env_activator_path%"
	rem install packages:
    if not exist "%default_packages_list%" ( 
		REM python packages list not existing case
        call :make_absolute_path_if_relative "%default_packages_list%"
		set "default_packages_list=!OUTPUT!"
        echo.
	    echo [Warning] List of default Python packages ("!default_packages_list!"^) not found. Skipping installation.
	    echo.
		goto end_of_activation
	) else ( 
		REM python packages list existing case
    	echo.
    	echo [Info] Installing packages:
    	echo.
    	python -m pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
    	echo.
    	echo [Info] Finished installing packages
        echo.
    	goto end_of_activation
	)
) else ( 
	REM python existing case
	rem check python version matches setting:
	call "%python_version_checker_path%" "%python_version%" "%python_exe_path%"
	if "!ERRORLEVEL!" neq "0" ( exit 11 ) 
	rem above: failed to determine python version. Error print and wait already in call
	if "!OUTPUT!"=="1" ( 
	   REM python version matching case
	   if exist "%env_activator_path%" ( 
		    REM env existing case
            rem activate env:
            call "%env_activator_path%"
			goto end_of_activation
	   ) else ( 
		    REM env not existing case
        	rem install virtual env:
        	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
            if "!ERRORLEVEL!" neq "0" ( exit 12 ) 
			rem above: failed to install venv. Error print and wait already in call
        	rem activate env:
            call "%env_activator_path%"
        	rem install packages:
            if not exist "%default_packages_list%" ( 
				REM python packages list not existing case
                call :make_absolute_path_if_relative "%default_packages_list%"
        		set "default_packages_list=!OUTPUT!"
                echo.
        	    echo [Warning] List of default Python packages ("!default_packages_list!!"^) not found. Skipping installation.
        	    echo.
        		goto end_of_activation
        	) else ( 
				REM python packages list existing case
            	echo.
            	echo [Info] Installing packages:
            	echo.
            	python -m pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
            	echo.
            	echo [Info] Finished installing packages
                echo.
            	goto end_of_activation
        	)
	   )  
	   rem above: end of env not existing case
	) else ( 
	   REM python version not matching case
	   if exist "%env_activator_path%" ( 
		    REM env existing case
	        rem ask user if he wants to recreate python and venv with current packages
            echo.
            echo [Warning] Installed Python version is not compatible with the version specified in "%settings_path%" (%python_version%^).
		    echo Do you want to locally for this program reinstall Python + virtual environment + current packages OR stay with current setup?
		    call :prompt_user
            if "!OUTPUT!"=="1" ( 
				REM user: yes case
			    rem activate to get current packages:
                call "%env_activator_path%"
                rem get current packages:
                call "%requirements_generator_path%" "%python_folder_folder_path%\tmp_requirement.txt"
			    if "!ERRORLEVEL!" neq "0" ( exit 13 ) 
				rem above: failed to generate package list. Error print and wait already in call
                rem reinstall python:
                call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%" "%install_tkinter%" "%install_tests%" "0"
			    if "!ERRORLEVEL!" neq "0" ( exit 14 ) 
				rem above: failed to reinstall python. Error print and wait already in call
			    rem reinstall virtual env:
			    call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
                if "!ERRORLEVEL!" neq "0" ( exit 15 ) 
				rem above: failed to reinstall venv. Error print and wait already in call
			    rem activate to reinstall packages:
                call "%env_activator_path%"
			    rem reinstall packages:
            	echo.
            	echo [Info] Installing packages:
            	echo.
            	python -m pip install -r "%python_folder_folder_path%\tmp_requirement.txt" --disable-pip-version-check --upgrade --no-cache-dir 
				del "%python_folder_folder_path%\tmp_requirement.txt" >nul 2>&1
            	echo.
            	echo [Info] Finished installing packages
                echo.
            	goto end_of_activation
		    ) else (  
				REM user: no case
			    rem activate:
                call "%env_activator_path%"
			    goto end_of_activation
		    )
	   ) else ( 
		REM env not existing case. User does not get asked for python reinstall since either way no venv lost
        	rem reinstall python:
            call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%" "%install_tkinter%" "%install_tests%" "0"
        	if "!ERRORLEVEL!" neq "0" ( exit 16 ) 
			rem above: failed to install python. Error print and wait already in call
        	rem install virtual env:
        	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
            if "!ERRORLEVEL!" neq "0" ( exit 17 )  
			rem above: failed to install venv. Error print and wait already in call
        	rem activate env:
            call "%env_activator_path%"
        	rem install packages:
            if not exist "%default_packages_list%" (  
				REM python packages list not existing case
                call :make_absolute_path_if_relative "%default_packages_list%"
        		set "default_packages_list=!OUTPUT!"
                echo.
        	    echo [Warning] List of default Python packages ("!default_packages_list!"^) not found. Skipping installation.
        	    echo.
        		goto end_of_activation
        	) else (  
				REM python packages list existing case
            	echo.
            	echo [Info] Installing packages:
            	echo.
            	python -m pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
            	echo.
            	echo [Info] Finished installing packages
                echo.
            	goto end_of_activation
        	)
	   ) 
	   rem above: end of env not existing case
    ) 
	rem above: end of python version not matching case
) 
rem above: end of python existing case

:end_of_activation
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

:: go to directory of main python code and execute it and return to folder of this file. Faulthandler catches python interpreter crash:
cd /d "%python_code_dir%"
python -X faulthandler "%python_code_path%"
set "py_errorlevel=%ERRORLEVEL%"
cd /d "%current_file_path%"

:: %py_errorlevel% is what the last python execution gives out in sys.exit({int_errorlevel}). Errorlevel not 0 (default is 1 for python crash) will run main_code.py or after_python_crash_code.py (depending on parameter restart_main_code_on_crash in non-user_settings.ini).
if %py_errorlevel% neq 0 ( 
	call :handle_python_crash 
) else (
    exit 0
)


:: ====================
:: ==== Functions: ====
:: ====================

::::::::::::::::::::::::::::::::::::::::::::::
:: function to handle python crashes:
::::::::::::::::::::::::::::::::::::::::::::::
:handle_python_crash
if "%restart_main_code_on_crash%" EQU "0" (
	rem run after_python_crash_code.py 
	if exist "%after_python_crash_code_path%" (
		rem go to directory of python code and execute it and return to folder of this file
		cd /d "%crash_python_code_dir%"
		python -X faulthandler "%after_python_crash_code_path%"
		set "py_errorlevel=%ERRORLEVEL%"
		cd /d "%current_file_path%"
	rem exit function if after_python_crash_code does not exist
	) else (
		exit 0 
	)
)   else (	
	rem run main_code.py again
	rem go to directory of python code and execute it and return to folder of this file:
	rem argument "crashed" indicated to the python code that it is a repeat call after a crash and can be checked for with sys.argv[-1]=="crashed"
	cd /d "%python_code_dir%"
	python -X faulthandler "%python_code_path%" "crashed" 
	set "py_errorlevel=%ERRORLEVEL%"
	cd /d "%current_file_path%"
)
if "%py_errorlevel%" neq "0" ( 
	call :handle_python_crash 
) else ( 
	exit 0 
)



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
        set "OUTPUT=%cd%"
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
	if !ERRORLEVEL!==1 (
		set "OUTPUT=1"
	) else (
		set "OUTPUT=0"
	)
GOTO :EOF
:: =================================================
:: =================================================