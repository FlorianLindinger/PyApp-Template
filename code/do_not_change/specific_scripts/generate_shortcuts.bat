:: ========================
:: --- Code Description ---
:: ========================

:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands:
@echo off

:: make this code local so no variables of a potential calling program are changed (EnableDelayedExpansion for delayed expasion in settings file):
setlocal EnableDelayedExpansion

:: define local variables (with relative paths being relative to this file)
set "settings_path=..\..\non-user_settings.ini"
set "cmd_copies_folder_path=..\cmd_exe_copies"
set "shortcut_creator_path=..\general_utilities\create_shortcut.bat"
set "program_starter_path=start_program.bat"

:: get current file path and remove trailing \
set "current_file_path=%~dp0"
set "current_file_path=%current_file_path:~0,-1%"
:: move to folder of this file (needed for relative path)
cd /d "%current_file_path%"

:: make paths absolute if not
call :make_absolute_path_if_relative "%settings_path%" 
set "settings_path=%OUTPUT%"

:: check if files exist
if not exist "%settings_path%" (
	echo: [Error] "%settings_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)

:: import settings from settings_path:
for /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( set "%%A=%%B" )

:: check if defined in settings_path
if "%icon_path%"=="" (
	echo: [Error] icon_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)
if "%settings_icon_path%"=="" (
	echo: [Error] settings_icon_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)
if "%stop_icon_path%"=="" (
	echo: [Error] stop_icon_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)
if "%user_settings_path%"=="" (
	echo: [Error] user_settings_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)
if "%shortcut_destination_path%"=="" (
	echo: [Error] shortcut_destination_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)
if "%log_path%"=="" (
	echo: [Error] log_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)
if "%process_id_file_path%"=="" (
	echo: [Error] process_id_file_path not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)

:: convert the path settings that are relative to settings file to absolute paths:
for %%I IN ("%settings_path%") DO set "settings_dir=%%~dpI"
cd /d "%settings_dir%"
call :make_absolute_path_if_relative "%icon_path%" 
set "icon_path=%OUTPUT%"
call :make_absolute_path_if_relative "%settings_icon_path%" 
set "settings_icon_path=%OUTPUT%"
call :make_absolute_path_if_relative "%stop_icon_path%" 
set "stop_icon_path=%OUTPUT%"
call :make_absolute_path_if_relative "%user_settings_path%" 
set "user_settings_path=%OUTPUT%"
call :make_absolute_path_if_relative "%shortcut_destination_path%" 
set "shortcut_destination_path=%OUTPUT%"
call :make_absolute_path_if_relative "%log_path%" 
set "log_path=%OUTPUT%"
call :make_absolute_path_if_relative "%process_id_file_path%" 
set "process_id_file_path=%OUTPUT%"
cd /d "%current_file_path%"

:: check if files exist
if not exist "%icon_path%" (
	echo: [Error] "%icon_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)
if not exist "%settings_icon_path%" (
	echo: [Error] "%settings_icon_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)
if not exist "%stop_icon_path%" (
	echo: [Error] "%stop_icon_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)
if not exist "%user_settings_path%" (
	echo: [Error] "%user_settings_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)

:: ======================
:: --- Code Execution ---
:: ======================

:: The following hacky shortcuts (via cmd.exe call) are generated for the abiltiy to add to taskbar. In order to have multiple cmd.exe-shortcuts in the taskbar, they all need separate renamed copies of cmd.exe:

:: generate cmd.exe copies
mkdir "%cmd_copies_folder_path%" > nul 2>&1
copy /y "%SystemRoot%\System32\cmd.exe" "%cmd_copies_folder_path%\cmd_1_%program_name%.exe" > nul 2>&1
copy /y "%SystemRoot%\System32\cmd.exe" "%cmd_copies_folder_path%\cmd_2_%program_name%.exe" > nul 2>&1
copy /y "%SystemRoot%\System32\cmd.exe" "%cmd_copies_folder_path%\cmd_3_%program_name%.exe" > nul 2>&1
copy /y "%SystemRoot%\System32\cmd.exe" "%cmd_copies_folder_path%\cmd_4_%program_name%.exe" > nul 2>&1

:: ==== add language fildes needed for cmd.exe ====
REM get name of current localization language
for /f "tokens=2,*" %%A in ('reg query "HKCU\Control Panel\Desktop" /v PreferredUILanguages 2^>nul') do (
	for %%L in (%%B) do (
	set "UI_LANG=%%L"
	goto :done
	)
)
:done
REM check if successful
if "%UI_LANG%"=="" (
	echo: [Error] Could not determine system language. Aborting. Press any key to exit.
	pause >nul 
	EXIT /b 2
)
REM add matching localization files needed for cmd.exe
mkdir "%cmd_copies_folder_path%\%UI_LANG%" > nul 2>&1
mkdir "%cmd_copies_folder_path%\mui_files" > nul 2>&1
copy /y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%cmd_copies_folder_path%\mui_files\cmd_1_%program_name%.exe.mui" > nul 2>&1
copy /y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%cmd_copies_folder_path%\mui_files\cmd_2_%program_name%.exe.mui" > nul 2>&1
copy /y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%cmd_copies_folder_path%\mui_files\cmd_3_%program_name%.exe.mui" > nul 2>&1
copy /y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%cmd_copies_folder_path%\mui_files\cmd_4_%program_name%.exe.mui" > nul 2>&1
copy /y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%cmd_copies_folder_path%\%UI_LANG%\cmd_1_%program_name%.exe.mui" > nul 2>&1
copy /y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%cmd_copies_folder_path%\%UI_LANG%\cmd_2_%program_name%.exe.mui" > nul 2>&1
copy /y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%cmd_copies_folder_path%\%UI_LANG%\cmd_3_%program_name%.exe.mui" > nul 2>&1
copy /y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%cmd_copies_folder_path%\%UI_LANG%\cmd_4_%program_name%.exe.mui" > nul 2>&1
:: ===================

:: create shortcut for starting the program:
call "%shortcut_creator_path%" "%shortcut_destination_path%\%start_name%.lnk" "%cmd_copies_folder_path%\cmd_1_%program_name%.exe" "/K %program_starter_path%" "%current_file_path%" "%icon_path%" "PyApp-Template"
:: create a shortcut for the settings.yaml file:
call "%shortcut_creator_path%" "%shortcut_destination_path%\%settings_name%.lnk" "%cmd_copies_folder_path%\cmd_2_%program_name%.exe" "/K START \"\" \"%user_settings_path%\"" "%current_file_path%" "%settings_icon_path%" "PyApp-Template"
:: creare shortcut for launcher without terminal and with output to log file:
call "%shortcut_creator_path%" "%shortcut_destination_path%\%start_no_terminal_name%.lnk" "%cmd_copies_folder_path%\cmd_3_%program_name%.exe" "/K general_utilities\batch_file\run_batch_with_file_output_and_no_terminal.bat %program_starter_path% \"%log_path%\" \"%process_id_file_path%.pid\""  "%current_file_path%" "%icon_path%" "PyApp-Template"
:: create shortcut for killing the running program:
call "%shortcut_creator_path%" "%shortcut_destination_path%\%stop_no_terminal_name%.lnk" "%cmd_copies_folder_path%\cmd_4_%program_name%.exe" "/K general_utilities\kill_process_with_id.bat \"%process_id_file_path%\"" "%current_file_path%" "%stop_icon_path%" "PyApp-Template"

:: check if sucessful
If not exist "%shortcut_destination_path%\%start_name%.lnk" (
	echo: [Error] Failed to create shortcut. Press any key to exit.
	pause > nul
	exit /b 2
)
If not exist "%shortcut_destination_path%\%settings_name%.lnk" (
	echo: [Error] Failed to create shortcut. Press any key to exit.
	pause > nul
	exit /b 2
)
If not exist "%shortcut_destination_path%\%start_no_terminal_name%.lnk" (
	echo: [Error] Failed to create shortcut. Press any key to exit.
	pause > nul
	exit /b 2
)
If not exist "%shortcut_destination_path%\%stop_no_terminal_name%.lnk" (
	echo: [Error] Failed to create shortcut. Press any key to exit.
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

:: =================================================
:: function that makes relative path (relative to current working directory) to :: absolute if not already. Works for empty path (relative) path:
:: Usage:
::    call :make_absolute_path_if_relative "%some_path%"
::    set "abs_path=%output%"
:: =================================================
:make_absolute_path_if_relative
    if "%~1"=="" (
        set "OUTPUT=%CD%"
    ) else (
	    set "OUTPUT=%~f1"
    )
goto :EOF
:: =================================================
