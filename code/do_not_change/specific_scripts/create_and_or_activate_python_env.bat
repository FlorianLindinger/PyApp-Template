:: ========================
:: --- Code Description ---
:: ========================





:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands &  make variables local & enable needed features:
@echo off & setlocal EnableDelayedExpansion

:: define local variables (with relative paths being relative to this file)
set "settings_path=..\..\non-user_settings.ini"
set "python_version_checker_path=..\general_utilities\python_environment\check_if_python_version_matches.bat"
set "portable_venv_creator_path=..\general_utilities\python_environment\create_portable_venv.bat"
set "portable_python_installer_path=..\general_utilities\python_environment\create_portable_python.bat"
set "requirements_generator_path=..\general_utilities\python_environment\generate_requirements.txt_no_version.bat"
set "python_folder_folder_path=..\..\py_env"
set "default_packages_list=%python_folder_folder_path%\default_python_packages.txt"
set "python_folder_path=%python_folder_folder_path%\py_dist"
set "env_activator_path=%python_folder_folder_path%\virt_env\activate.bat"
set "python_exe_path=%python_folder_path%\python.exe"
SET "tmp_txt_path=tmp_requirements.txt"

:: move to folder of this file (needed for relative paths).
:: current_file_path variable needed as workaround for nieche Windows bug where this file gets called with quotation marks:
set "current_file_path=%~dp0"
cd /d "%current_file_path%"

:: make paths absolute if not
call :set_abs_path "%python_version_checker_path%" "python_version_checker_path"
call :set_abs_path "%python_exe_path%" "python_exe_path"
call :set_abs_path "%portable_venv_creator_path%" "portable_venv_creator_path"
call :set_abs_path "%portable_python_installer_path%" "portable_python_installer_path"
call :set_abs_path "%requirements_generator_path%" "requirements_generator_path"
call :set_abs_path "%env_activator_path%" "env_activator_path"
call :set_abs_path "%python_folder_folder_path%" "python_folder_folder_path"

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
::    install_tools
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( set "%%A=%%B" )

:: convert true/false to 1/0
if "%install_tkinter%"=="true" (
	set "install_tkinter=1"
) else ( if "%install_tkinter%"=="false" (
	set "install_tkinter=0"
))
if "%install_tests%"=="true" (
	set "install_tests=1"
) else ( if "%install_tests%"=="false" (
	set "install_tests=0"
))
if "%install_tools%"=="true" (
	set "install_tools=1"
) else ( if "%install_tools%"=="false" (
	set "install_tools=0"
))

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
   call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%" "%install_tkinter%" "%install_tests%" "%install_tools%" "0"
   if "!ERRORLEVEL!" neq "0" ( 
		echo [Error 9] Failed to install Python. Aborting. Press any key to exit.
		pause > nul
		exit 9 
   ) 
	echo.
	echo =============================================
	echo ==== Creating Virtual Python Environment ====
	echo =============================================
	echo.
	REM install virtual env:
	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
   if "!ERRORLEVEL!" neq "0" ( 
		echo [Error 10] Failed to create virtual Python environment. Aborting. Press any key to exit.
		pause > nul
		exit 10 
   ) 
	echo.
	echo =============================================
	REM activate env:
   call "%env_activator_path%"
	REM install packages:
   if not exist "%default_packages_list%" ( 
		REM python packages list not existing case
      call :set_abs_path "%default_packages_list%" "default_packages_list"
      echo.
	   echo [Warning] List of default Python packages ("!default_packages_list!"^) not found. Skipping installation.
	) else ( 
		REM python packages list existing case
      echo.
      echo [Info] Installing packages:
      echo.
		REM can't use pip directly here because pip is implemented in portable venv as batch and does not return (alternatively works if called with "call"):
      python -m pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
      echo.
      echo [Info] Finished installing packages
	)
) else ( 
	REM python existing case
	REM check python version matches setting:
	call "%python_version_checker_path%" "%python_version%" "%python_exe_path%"
	if "!OUTPUT!" == "2" ( 
		echo [Error 11] Failed to determine Python version. Aborting. Press any key to exit.
		pause > nul
		exit 11 
	) 
	if "!OUTPUT!"=="1" ( 
	   	REM python version matching case
	   	if exist "%env_activator_path%" ( 
			REM env existing case
        	REM activate env and exit:
        	goto :success_exit
		) else ( 
		    REM env not existing case
			echo.
			echo =============================================
			echo ==== Creating Virtual Python Environment ====
			echo =============================================
			echo.
        	REM install virtual env:
        	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
            if "!ERRORLEVEL!" neq "0" ( 
				echo [Error 12] Failed to create virtual Python environment. Aborting. Press any key to exit.
				pause > nul
				exit 12 
			) 
        	if not exist "%env_activator_path%" ( 
				REM env not existing case
				echo.
				echo [Error 13] Virtual environment activator not found at "%env_activator_path%". Aborting. Press any key to exit.
				pause > nul
				exit 13
	      )
			REM activate env:
         call "%env_activator_path%"
			REM install packages:
         if not exist "%default_packages_list%" ( 
				REM python packages list not existing case
            call :set_abs_path "%default_packages_list%" "default_packages_list"
            echo.
        	   echo [Warning] List of default Python packages ("!default_packages_list!!"^) not found. Skipping installation.
        	) else ( 
				REM python packages list existing case
            echo.
            echo [Info] Installing packages:
            echo.
				REM can't use pip directly here because pip is implemented in portable venv as batch and does not return (alternatively works if called with "call"):
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
         	echo.
          	echo [Warning] Installed Python version is not compatible with the version specified in "%settings_path%" (%python_version%^).
		    call :prompt_user "Do you want to reinstall Python locally inside this program + a virtual environment + current packages OR stay with current setup? (Y/N)"
            if "!OUTPUT!"=="1" ( 
				REM user: yes case
			   	REM activate to get current packages:
            	call "%env_activator_path%"
            	REM get current packages:
            	call "%requirements_generator_path%" "%tmp_txt_path%"
			   	if "!ERRORLEVEL!" neq "0" ( 
					echo [Error 13] Failed to generate current packages list. Aborting. Press any key to exit.
					pause > nul
					exit 13 
				) 
            	echo.
				echo =============================
				echo ==== Reinstalling Python ====
				echo =============================
				echo.
				REM reinstall python:
            	call "%portable_python_installer_path%" "%python_version%" "%python_folder_folder_path%" "%install_tkinter%" "%install_tests%" "0"
			   	if "!ERRORLEVEL!" neq "0" ( 
					echo [Error 14] Failed to reinstall Python. Aborting. Press any key to exit.
					pause > nul
					exit 14 
				) 
			    echo.
				echo ===============================================
				echo ==== Recreating Virtual Python Environment ====
				echo ===============================================
				echo.
				REM reinstall virtual env:
			    call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
             	if "!ERRORLEVEL!" neq "0" ( 
					echo [Error 15] Failed to reinstall virtual environment. Aborting. Press any key to exit.
					pause > nul
					exit 15 
				) 
			    REM activate to reinstall packages:
                call "%env_activator_path%"
			    REM reinstall packages:
            	echo.
            	echo [Info] Installing packages:
            	echo.
				REM can't use pip directly here because pip is implemented in portable venv as batch and does not return (alternatively works if called with "call"):
            	python -m pip install -r "%tmp_txt_path%" --disable-pip-version-check --upgrade --no-cache-dir 
				del "%tmp_txt_path%" >nul 2>&1
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
            if "!ERRORLEVEL!" neq "0" ( 
				   echo [Error 16] Failed to reinstall Python. Aborting. Press any key to exit.
				   pause > nul
				   exit 16 
				) 
        	echo.
			echo =============================================
			echo ==== Creating Virtual Python Environment ====
			echo =============================================
			echo.
			REM install virtual env:
        	call "%portable_venv_creator_path%" "%python_folder_folder_path%" "%python_folder_path%"
         if "!ERRORLEVEL!" neq "0" ( 
				echo [Error 17] Failed to install virtual environment. Aborting. Press any key to exit.
				pause > nul
				exit 17 
			)  
        	REM activate env:
            call "%env_activator_path%"
        	REM install packages:
            if not exist "%default_packages_list%" (
				REM python packages list not existing case
                call :set_abs_path "%default_packages_list%" "default_packages_list"
                echo.
        	    echo [Warning] List of default Python packages ("!default_packages_list!"^) not found. Skipping installation.
        	) else (  
				REM python packages list existing case
				REM check if any package listed:
				findstr /R /V "^\s*$" "%default_packages_list%" > nul && (
					echo.
					echo [Info] Installing packages:
					echo.
					REM can't use pip directly here because pip is implemented in portable venv as batch and does not return (alternatively works if called with "call"):
					python -m pip install -r "%default_packages_list%" --disable-pip-version-check --upgrade --no-cache-dir 
					echo.
					echo [Info] Finished installing packages
				)
          )
	    ) & REM end of env not existing case
   ) & REM end of python version not matching case
) & REM end of python existing case

:: exit
goto :success_exit

:success_exit
echo 21
endlocal & call "%env_activator_path%"
exit /b 0

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

::::::::::::::::::::::::::::::::::::::::::::::::
:: function that prompts user with prompt=arg1 and sets OUTPUT=1 for y and OUTPUT=0 for n.
::::::::::::::::::::::::::::::::::::::::::::::::
:prompt_user
setlocal
set "ans="
set "OUT="
:ask
set /p "ans=%~1"
if /i "%ans%"=="y" (
    set "OUT=1"
) else if /i "%ans%"=="n" (
    set "OUT=0"
) else (
    echo Invalid input. Please enter y or n.
    goto ask
)
endlocal & set "OUTPUT=%OUT%"
goto :EOF
:: =================================================
