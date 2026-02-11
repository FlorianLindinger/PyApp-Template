:: ========================
:: --- Code Description ---
:: ========================

:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands & make variables local & allow for delayed expansion (needed for imported settings with ! inside)
@echo off & setlocal EnableDelayedExpansion

:: define local variables (with relative paths being relative to this file)
set "settings_path=..\..\non-user_settings.ini"
set "start_program_batch_path=1.bat"
set "open_settings_file_batch_path=open_settings_file.bat"
set "create_shortcut_batch_path=..\general_utilities\create_shortcut.bat"
:: no spaces allowed for 2 settings below
set "run_batch_with_file_output_and_no_terminal_batch_path=2.bat"
set "kill_process_with_id_batch_path=3.bat"
set "do_not_change_folder_path=.."
set "python_exe_path=..\python_runtime\python.exe"
set "specific_scripts_path=."
rem set "python_exe_path_relative_to_do_not_change=python_runtime\python.exe"
rem set "batch_runner_path_relative_to_do_not_change=specific_scripts\run_batch.py"
set "batch_runner_path_relative_to_specific_scripts=run_batch.py"

:: get current file path and remove trailing \
set "current_file_path=%~dp0"
set "current_file_path=%current_file_path:~0,-1%"
:: move to folder of this file (needed for relative path)
cd /d "%current_file_path%"

:: make paths absolute if not
call :set_abs_path "%settings_path%" "settings_path"
rem call :set_abs_path "%do_not_change_folder_path%" "do_not_change_folder_path"
call :set_abs_path "%python_exe_path%" "python_exe_path"
call :set_abs_path "%specific_scripts_path%" "specific_scripts_path"

:: warn if target does not exist
if not exist "%specific_scripts_path%" (
	echo [Warning] Shortcut target "%specific_scripts_path%" does not exist.
)

:: check if files exist
if not exist "%settings_path%" (
	echo [Error] "%settings_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)

:: import settings from settings_path:
for /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( set "%%A=%%B" )

:: check if defined in settings_path
if "%icon_path%"=="" (
	echo [Error] icon_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)
if "%settings_icon_path%"=="" (
	echo [Error] settings_icon_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)
if "%stop_icon_path%"=="" (
	echo [Error] stop_icon_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)
if "%shortcut_destination_path%"=="" (
	echo [Error] shortcut_destination_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)

:: convert the path settings that are relative to settings file to absolute paths:
for %%I IN ("%settings_path%") DO set "settings_dir=%%~dpI"
cd /d "%settings_dir%"
call :set_abs_path "%icon_path%" "icon_path"
call :set_abs_path "%settings_icon_path%" "settings_icon_path"
call :set_abs_path "%stop_icon_path%" "stop_icon_path"
call :set_abs_path "%shortcut_destination_path%" "shortcut_destination_path"
cd /d "%current_file_path%"

:: check if files exist
if not exist "%icon_path%" (
	echo [Error] "%icon_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)
if not exist "%settings_icon_path%" (
	echo [Error] "%settings_icon_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)
if not exist "%stop_icon_path%" (
	echo [Error] "%stop_icon_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)

:: ======================
:: --- Code Execution ---
:: ======================

:: %create_shortcut_batch_path% has arguments "<name>" "<target>" "<target-args>" "<working-dir>" "<icon-path>" "<description>" "<appid>"

:: create shortcut for starting the program:
set "name=%shortcut_destination_path%\%start_name%.lnk"
set "target=%python_exe_path%"
set "args=""%batch_runner_path_relative_to_specific_scripts%"" ""%start_program_batch_path%"" test3"
set "wdir=%specific_scripts_path%"
set "icon=%icon_path%"
set "description=%program_name%"
set "app_id=test3"
call "%create_shortcut_batch_path%" "%name%" "%target%" "%args%" "%wdir%" "%icon%" "%description%" "%app_id%"

pause
exit /b

:: create a shortcut for the settings file:
set "name=%shortcut_destination_path%\%settings_name%.lnk"
set "target=%python_exe_path_relative_to_do_not_change%"
set "args=""%batch_runner_path_relative_to_do_not_change%"" ""%open_settings_file_batch_path%"" %program_name%2"
set "wdir=""%do_not_change_folder_path%"""
set "icon=%settings_icon_path%"
set "description=%program_name%"
set "app_id=%program_name%2"
call "%create_shortcut_batch_path%" "%name%" "%target%" "%args%" "%wdir%" "%icon%" "%description%" "%app_id%"

:: create shortcut for launcher without terminal and with output to log file:
set "name=%shortcut_destination_path%\%start_no_terminal_name%.lnk"
set "target=%python_exe_path_relative_to_do_not_change%"
set "args=""%batch_runner_path_relative_to_do_not_change%"" ""%run_batch_with_file_output_and_no_terminal_batch_path%"" %program_name%3"
set "wdir=""%do_not_change_folder_path%"""
set "icon=%icon_path%"
set "description=%program_name%"
set "app_id=%program_name%3"
call "%create_shortcut_batch_path%" "%name%" "%target%" "%args%" "%wdir%" "%icon%" "%description%" "%app_id%"

:: create shortcut for killing the running program:
set "name=%shortcut_destination_path%\%stop_no_terminal_name%.lnk"
set "target=%python_exe_path_relative_to_do_not_change%"
set "args=""%batch_runner_path_relative_to_do_not_change%"" ""%kill_process_with_id_batch_path%"" %program_name%4"
set "wdir=""%do_not_change_folder_path%"""
set "icon=%stop_icon_path%"
set "description=%program_name%"
set "app_id=%program_name%4"
call "%create_shortcut_batch_path%" "%name%" "%target%" "%args%" "%wdir%" "%icon%" "%description%" "%app_id%"

:: ============================

:: check if successful
If not exist "%shortcut_destination_path%\%start_name%.lnk" (
	echo [Error] Failed to create shortcut. Press any key to exit.
	pause > nul
	exit /b 2
)
If not exist "%shortcut_destination_path%\%settings_name%.lnk" (
	echo [Error] Failed to create shortcut. Press any key to exit.
	pause > nul
	exit /b 2
)
If not exist "%shortcut_destination_path%\%start_no_terminal_name%.lnk" (
	echo [Error] Failed to create shortcut. Press any key to exit.
	pause > nul
	exit /b 2
)
If not exist "%shortcut_destination_path%\%stop_no_terminal_name%.lnk" (
	echo [Error] Failed to create shortcut. Press any key to exit.
	pause > nul
	exit /b 2
)

:: print info, wait for any key and exit:
echo.
echo Created shortcuts in "%shortcut_destination_path%": 
echo  - "%start_name%"
echo  - "%start_no_terminal_name%"
echo  - "%stop_no_terminal_name%"
echo  - "%settings_name%"
echo.
echo Press any key to exit.
pause > nul
EXIT /b 0

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

