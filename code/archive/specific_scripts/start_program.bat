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
set "icon_changer_path=..\general_utilities\window_icon_changer\change_icon.py_standalone_compiled\run.exe"
set "python_app_id_changer_path=do_not_change\specific_scripts\change_AppID_and_run_py_script.py"

:: move to folder of this file (needed for relative paths).
:: current_file_path variable needed as workaround for nieche Windows bug where this file gets called with quotation marks:
set "current_file_path=%~dp0"
cd /d "%current_file_path%"

:: make paths absolute if not
call :set_abs_path "%settings_path%" "settings_path"
call :set_abs_path "%environment_activator_path%" "environment_activator_path" 
call :set_abs_path "%icon_changer_path%" "icon_changer_path"

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
if "%python_code_name%"=="" (
	echo [Error 6] Variable python_code_name not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit 6
)

:: give default values if undefined
if "%restart_main_code_on_crash%"=="" (
	set "restart_main_code_on_crash=false"
)
if "%use_global_python%"=="" (
	set "use_global_python=false"
)
if "%python_version%"=="" (
	set "python_version=3"
)

:: move to directory of settings file to use its variables relative to it
FOR %%I IN ("%settings_path%") DO set "settings_dir=%%~dpI"
cd /d "%settings_dir%"

:: convert to absolute paths (now relative to settings file)
call :set_abs_path "%icon_path%" "icon_path"
call :set_abs_path "%python_code_name%" "python_code_name"
call :set_abs_path "%after_python_crash_code_name%" "after_python_crash_code_name"

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
if "%use_global_python%"=="false" (
	call "%environment_activator_path%"
	if %errorlevel% neq 0 (
		echo.
		echo [Error 7] Failed to activate or create the Python environment (see above^). Aborting. Press any key to exit.
		pause > nul
		exit 7
	)
)

:: Execute python code. Faulthandler catches python interpreter crash:
if "%use_global_python%"=="false" (
	call python -X faulthandler "%python_app_id_changer_path%" "%python_code_name%" "%~1"
) else (
	py -%python_version% -X faulthandler "%python_app_id_changer_path%" "%python_code_name%" "%~1"
)
set "py_errorlevel=%ERRORLEVEL%"

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
		if "%use_global_python%"=="false" (
			call python -X faulthandler "%after_python_crash_code_name%"
		) else (
			py -%python_version% -X faulthandler "%after_python_crash_code_name%"
		)
		set "py_errorlevel=%ERRORLEVEL%"
	REM exit function if after_python_crash_code does not exist
	) else (
		exit 0 
	)
)   else (	
	REM run main_code.py again
	REM argument "crashed" indicated to the python code that it is a repeat call after a crash and can be checked for with sys.argv[-1]=="crashed"
	if "%use_global_python%"=="false" (
		call python -X faulthandler "%python_code_name%" "crashed" 
	) else (
		py -%python_version% -X faulthandler "%python_code_name%" "crashed"
	)
	set "py_errorlevel=%ERRORLEVEL%"
)
if "%py_errorlevel%" neq "0" ( 
	call :handle_python_crash 
) else ( 
	exit 0 
)
:: =================================================

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

