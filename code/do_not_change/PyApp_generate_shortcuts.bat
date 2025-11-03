:: ========================
:: --- Code Description ---
:: ========================

:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands:
@ECHO OFF

:: make this code local so no variables of a potential calling program are changed (ENABLEDELAYEDEXPANSION for delayed expasion in settings file):
SETLOCAL ENABLEDELAYEDEXPANSION

:: define local variables (with relative paths being relative to this file)
SET "settings_path=..\non-user_settings.ini"

:: get current file path and remove trailing \
SET "current_file_path=%~dp0"
SET "current_file_path=%current_file_path:~0,-1%"
:: move to folder of this file (needed for relative path)
CD /D "%current_file_path%"

:: make paths absolute if not
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%settings_path%" 
SET "settings_path=%OUTPUT%"

:: check if files exist
IF NOT exist "%settings_path%" (
	echo: [Error] "%settings_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)

:: import settings from settings_path:
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( SET "%%A=%%B" )

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
FOR %%I IN ("%settings_path%") DO SET "settings_dir=%%~dpI"
CD /D "%settings_dir%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%icon_path%" 
SET "icon_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%settings_icon_path%" 
SET "settings_icon_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%stop_icon_path%" 
SET "stop_icon_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%user_settings_path%" 
SET "user_settings_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%shortcut_destination_path%" 
SET "shortcut_destination_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%log_path%" 
SET "log_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%process_id_file_path%" 
SET "process_id_file_path=%OUTPUT%"
CD /D "%current_file_path%"

:: check if files exist
IF NOT exist "%icon_path%" (
	echo: [Error] "%icon_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)
IF NOT exist "%settings_icon_path%" (
	echo: [Error] "%settings_icon_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)
IF NOT exist "%stop_icon_path%" (
	echo: [Error] "%stop_icon_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)
IF NOT exist "%user_settings_path%" (
	echo: [Error] "%user_settings_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)

:: ======================
:: --- Code Execution ---
:: ======================

:: The following hacky shortcuts (via cmd.exe call) are generated for the abiltiy to add to taskbar. In order to have multiple cmd.exe-shortcuts in the taskbar, they all need separate renamed copies of cmd.exe:

:: generate cmd.exe copies
MKDIR CMD_exes > NUL 2>&1
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_1_%program_name%.exe" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_2_%program_name%.exe" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_3_%program_name%.exe" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_4_%program_name%.exe" > NUL 2>&1

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
	ECHO: [Error] Could not determine system language. Aborting. Press any key to exit.
	PAUSE >NUL 
	EXIT /B 2
)
REM add matching localization files needed for cmd.exe
MKDIR "%current_file_path%\CMD_exes\%UI_LANG%" > NUL 2>&1
MKDIR "%current_file_path%\CMD_exes\mui_files" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\mui_files\cmd_1_%program_name%.exe.mui" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\mui_files\cmd_2_%program_name%.exe.mui" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\mui_files\cmd_3_%program_name%.exe.mui" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\mui_files\cmd_4_%program_name%.exe.mui" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\%UI_LANG%\cmd_1_%program_name%.exe.mui" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\%UI_LANG%\cmd_2_%program_name%.exe.mui" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\%UI_LANG%\cmd_3_%program_name%.exe.mui" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\%UI_LANG%\cmd_4_%program_name%.exe.mui" > NUL 2>&1
:: ===================

:: create shortcut for starting the program:
call utilities\create_shortcut.bat "%shortcut_destination_path%\%start_name%.lnk" "%current_file_path%\CMD_exes\cmd_1_%program_name%.exe" "/K PyApp_start_program.bat" "%current_file_path%" "%icon_path%" "PyApp-Template"
:: create a shortcut for the settings.yaml file:
call utilities\create_shortcut.bat "%shortcut_destination_path%\%settings_name%.lnk" "%current_file_path%\CMD_exes\cmd_2_%program_name%.exe" "/C START \"\" \"%user_settings_path%\"" "%current_file_path%" "%settings_icon_path%" "PyApp-Template"
:: creare shortcut for launcher without terminal and with output to log file:
call utilities\create_shortcut.bat "%shortcut_destination_path%\%start_no_terminal_name%.lnk" "%current_file_path%\CMD_exes\cmd_3_%program_name%.exe" "/C run_batch_with_file_output_and_no_terminal.bat PyApp_start_program.bat \"%log_path%\" \"%process_id_file_path%.pid\""  "%current_file_path%" "%icon_path%" "PyApp-Template"
:: create shortcut for killing the running program:
call utilities\create_shortcut.bat "%shortcut_destination_path%\%stop_no_terminal_name%.lnk" "%current_file_path%\CMD_exes\cmd_4_%program_name%.exe" "/C kill_process_with_id.bat \"%process_id_file_path%\"" "%current_file_path%" "%stop_icon_path%" "PyApp-Template"

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
ECHO:
ECHO: Created shortcuts "%start_name%", "%start_no_terminal_name%", "%stop_no_terminal_name%" ^& "%settings_name%" in "%shortcut_destination_path%". Press any key to exit.
pause > nul
EXIT /B 0

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
