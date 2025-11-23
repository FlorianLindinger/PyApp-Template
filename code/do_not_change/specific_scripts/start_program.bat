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
set "environment_activator_path=create_and_or_activate_python_env.bat"
set "icon_changer_path=..\general_utilities\change_icon.exe"

:: move to folder of this file (needed for relative paths).
:: current_file_path variable needed as workaround for nieche Windows bug where this file gets called with quotation marks:
set "current_file_path=%~dp0"
cd /d "%current_file_path%"

:: make paths absolute if not
call :make_absolute_path_if_relative "%settings_path%" 
set "settings_path=%OUTPUT%"
call :make_absolute_path_if_relative "%environment_activator_path%" 
set "environment_activator_path=%OUTPUT%"

:: check if files exist
if NOT exist "%settings_path%" (
	echo [Error 1] "%settings_path%" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 1
)
if NOT exist "%environment_activator_path%" (
	echo [Error 2] "%environment_activator_path%" file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit 2
)

:: import settings from %settings_path%:
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( set "%%A=%%B" )

:: check if defined in settings_path
if "%icon_path%"=="" (
	echo [Error 5] Variable icon_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit 5
)
if "%python_code_path%"=="" (
	echo [Error 6] Variable python_code_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit 6
)

:: give default values if undefined
if "%restart_main_code_on_crash%"=="" (
	set "restart_main_code_on_crash=false"
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

:: activate or create & activate virtual Python environment
call "%environment_activator_path%"

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
if "%restart_main_code_on_crash%"=="false" (
	REM run after_python_crash_code.py 
	if exist "%after_python_crash_code_path%" (
		REM go to directory of python code and execute it and return to folder of this file
		cd /d "%crash_python_code_dir%"
		python -X faulthandler "%after_python_crash_code_path%"
		set "py_errorlevel=%ERRORLEVEL%"
		cd /d "%current_file_path%"
	REM exit function if after_python_crash_code does not exist
	) else (
		exit 0 
	)
)   else (	
	REM run main_code.py again
	REM go to directory of python code and execute it and return to folder of this file:
	REM argument "crashed" indicated to the python code that it is a repeat call after a crash and can be checked for with sys.argv[-1]=="crashed"
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