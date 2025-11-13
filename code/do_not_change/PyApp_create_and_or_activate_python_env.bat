:: ========================
:: --- Code Description ---
:: ========================





:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands &  make variables local & enable needed features:
@echo off & setlocal EnableDelayedExpansion

:: define local variables (with relative paths being relative to this file)
set "settings_path=..\non-user_settings.ini"
set "python_version_checker_path=utilities\python_environment\check_if_python_version_matches.bat"
set "portable_venv_creator_path=utilities\python_environment\create_portable_venv.bat"
set "portable_python_installer_path=utilities\python_environment\create_portable_python.bat"
set "requirements_generator_path=utilities\python_environment\generate_requirements.txt_no_version.bat"
set "python_folder_folder_path=..\python_environment"
set "default_packages_list=%python_folder_folder_path%\default_python_packages.txt"
set "python_folder_path=%python_folder_folder_path%\portable_python"
set "env_activator_path=%python_folder_folder_path%\virtual_environment\activate.bat"
set "python_exe_path=%python_folder_path%\python.exe"

:: move to folder of this file (needed for relative paths).
:: current_file_path variable needed as workaround for nieche Windows bug where this file gets called with quotation marks:
set "current_file_path=%~dp0"
cd /d "%current_file_path%"

:: make paths absolute if not
call :make_absolute_path_if_relative "%python_version_checker_path%" 
set "python_version_checker_path=%OUTPUT%"
call :make_absolute_path_if_relative "%python_exe_path%" 
set "python_exe_path=%OUTPUT%"
call :make_absolute_path_if_relative "%portable_venv_creator_path%" 
set "portable_venv_creator_path=%OUTPUT%"
call :make_absolute_path_if_relative "%portable_python_installer_path%" 
set "portable_python_installer_path=%OUTPUT%"
call :make_absolute_path_if_relative "%requirements_generator_path%" 
set "requirements_generator_path=%OUTPUT%"
call :make_absolute_path_if_relative "%env_activator_path%" 
set "env_activator_path=%OUTPUT%"
call :make_absolute_path_if_relative "%python_folder_folder_path%" 
set "python_folder_folder_path=%OUTPUT%"

:: check if files exist
if NOT exist "%python_version_checker_path%" (
	echo [Error 1] "%python_version_checker_path%" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 1
)
if NOT exist "%portable_venv_creator_path%" (
	echo [Error 2] "%portable_venv_creator_path%" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 2
)
if NOT exist "%portable_python_installer_path%" (
	echo [Error 3] "%portable_python_installer_path%" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 3
)

:: Import settings from %settings_path%: 
:: Used optional settings: 
::    python_version
::    install_tkinter
::    install_tests
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( set "%%A=%%B" )

:: ======================
:: --- Code Execution ---
:: ======================

if not exist "%python_exe_path%" ( 
	REM python not existing case
	echo.
	echo ===========================
	echo ==== Installing Python ====
	echo ===========================
	echo.
	REM install python: "0" in next line means no installation of Python docs:
    call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%" "%install_tkinter%" "%install_tests%" "0"
	if "!ERRORLEVEL!" neq "0" ( exit 9 ) 
	REM above: failed to install python. Error print and wait already in call
	echo.
	echo =============================================
	echo ==== Creating Virtual Python Environment ====
	echo =============================================
	echo.
	REM install virtual env:
	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
    if "!ERRORLEVEL!" neq "0" ( exit 10 ) 
	REM above: failed to install venv. Error print and wait already in call
	REM activate env:
    call "%env_activator_path%"
	REM install packages:
    if not exist "%default_packages_list%" ( 
		REM python packages list not existing case
        call :make_absolute_path_if_relative "%default_packages_list%"
		set "default_packages_list=!OUTPUT!"
        echo.
	    echo [Warning] List of default Python packages ("!default_packages_list!"^) not found. Skipping installation.
	) else ( 
		REM python packages list existing case
    	echo.
    	echo [Info] Installing packages:
    	echo.
    	python -m pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
    	echo.
    	echo [Info] Finished installing packages
	)
) else ( 
	REM python existing case
	REM check python version matches setting:
	call "%python_version_checker_path%" "%python_version%" "%python_exe_path%"
	if "!ERRORLEVEL!" neq "0" ( exit 11 ) 
	REM above: failed to determine python version. Error print and wait already in call
	if "!OUTPUT!"=="1" ( 
	   REM python version matching case
	   if exist "%env_activator_path%" ( 
		    REM env existing case
            REM activate env:
            call "%env_activator_path%"
	   ) else ( 
		    REM env not existing case
			echo.
			echo =============================================
			echo ==== Creating Virtual Python Environment ====
			echo =============================================
			echo.
        	REM install virtual env:
        	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
            if "!ERRORLEVEL!" neq "0" ( exit 12 ) 
			REM above: failed to install venv. Error print and wait already in call
        	REM activate env:
            call "%env_activator_path%"
        	REM install packages:
            if not exist "%default_packages_list%" ( 
				REM python packages list not existing case
                call :make_absolute_path_if_relative "%default_packages_list%"
        		set "default_packages_list=!OUTPUT!"
                echo.
        	    echo [Warning] List of default Python packages ("!default_packages_list!!"^) not found. Skipping installation.
        	) else ( 
				REM python packages list existing case
            	echo.
            	echo [Info] Installing packages:
            	echo.
            	python -m pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
            	echo.
            	echo [Info] Finished installing packages
        	)
	   )  
	   REM above: end of env not existing case
	) else ( 
	   REM python version not matching case
	   if exist "%env_activator_path%" ( 
		    REM env existing case
	        REM ask user if he wants to recreate python and venv with current packages
            echo.
            echo [Warning] Installed Python version is not compatible with the version specified in "%settings_path%" (%python_version%^).
		    echo Do you want to locally for this program reinstall Python + virtual environment + current packages OR stay with current setup?
		    call :prompt_user
            if "!OUTPUT!"=="1" ( 
				REM user: yes case
			    REM activate to get current packages:
                call "%env_activator_path%"
                REM get current packages:
                call "%requirements_generator_path%" "%python_folder_folder_path%\tmp_requirement.txt"
			    if "!ERRORLEVEL!" neq "0" ( exit 13 ) 
				REM above: failed to generate package list. Error print and wait already in call
            	echo.
				echo =============================
				echo ==== Reinstalling Python ====
				echo =============================
				echo.
				REM reinstall python:
                call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%" "%install_tkinter%" "%install_tests%" "0"
			    if "!ERRORLEVEL!" neq "0" ( exit 14 ) 
				REM above: failed to reinstall python. Error print and wait already in call
			    echo.
				echo ===============================================
				echo ==== Recreating Virtual Python Environment ====
				echo ===============================================
				echo.
				REM reinstall virtual env:
			    call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
                if "!ERRORLEVEL!" neq "0" ( exit 15 ) 
				REM above: failed to reinstall venv. Error print and wait already in call
			    REM activate to reinstall packages:
                call "%env_activator_path%"
			    REM reinstall packages:
            	echo.
            	echo [Info] Installing packages:
            	echo.
            	python -m pip install -r "%python_folder_folder_path%\tmp_requirement.txt" --disable-pip-version-check --upgrade --no-cache-dir 
				del "%python_folder_folder_path%\tmp_requirement.txt" >nul 2>&1
            	echo.
            	echo [Info] Finished installing packages
		    ) else (  
				REM user: no case
			    REM activate:
                call "%env_activator_path%"
		    )
	   ) else ( 
		REM env not existing case. User does not get asked for python reinstall since either way no venv lost
        	echo.
			echo =============================
			echo ==== Reinstalling Python ====
			echo =============================
			echo.
			REM reinstall python:
            call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%" "%install_tkinter%" "%install_tests%" "0"
        	if "!ERRORLEVEL!" neq "0" ( exit 16 ) 
			REM above: failed to install python. Error print and wait already in call
        	echo.
			echo =============================================
			echo ==== Creating Virtual Python Environment ====
			echo =============================================
			echo.
			REM install virtual env:
        	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
            if "!ERRORLEVEL!" neq "0" ( exit 17 )  
			REM above: failed to install venv. Error print and wait already in call
        	REM activate env:
            call "%env_activator_path%"
        	REM install packages:
            if not exist "%default_packages_list%" (
				REM python packages list not existing case
                call :make_absolute_path_if_relative "%default_packages_list%"
        		set "default_packages_list=!OUTPUT!"
                echo.
        	    echo [Warning] List of default Python packages ("!default_packages_list!"^) not found. Skipping installation.
        	) else (  
				REM python packages list existing case
				REM check if any package listed:
				findstr /R /V "^\s*$" "%default_packages_list%" > nul && (
					echo.
					echo [Info] Installing packages:
					echo.
					python -m pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
					echo.
					echo [Info] Finished installing packages
				)
        	)
	    ) & REM end of env not existing case
    ) & REM end of python version not matching case
	echo.
	echo =============================================
	echo.
) & REM end of python existing case

:: exit
exit \b 0



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
:: =================================================