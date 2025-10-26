:: ========================
:: --- Code Description ---
:: ========================

:: =========================
:: --- Setup & Variables ---
:: =========================

:: turn off printing of commands:
@ECHO OFF

:: make this code local so no variables of a potential calling program are changed:
SETLOCAL ENABLEDELAYEDEXPANSION

:: define local variables 
SET "settings_path=%~1"

:: move to folder of this file (needed for relative path shortcuts)
:: current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path=%~dp0"
CD /D "%current_file_path%"

:: ======================
:: --- Code Execution ---
:: ======================

:: check if settings file exist
IF NOT exist "%settings_path%" (
	echo: [Error] Need to define existing settings path. Defined "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)

:: import settings from settings_path:
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( SET "%%A=%%B" )

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

:: The following hacky shortcuts (via cmd.exe call) are generated for the abiltiy to add to taskbar. In order to have multiple cmd.exe-shortcuts in the taskbar, they all need separate renamed copies of cmd.exe:

:: generate cmd.exe copies
MKDIR CMD_exes > NUL 2>&1
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_1_%program_name%.exe"
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_2_%program_name%.exe"
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_3_%program_name%.exe"
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_4_%program_name%.exe"

:: ==== add language fildes needed for cmd.exe ====
:: get name of current localization language
for /f "tokens=2,*" %%A in ('reg query "HKCU\Control Panel\Desktop" /v PreferredUILanguages 2^>nul') do (
	for %%L in (%%B) do (
	set "UI_LANG=%%L"
	goto :done
	)
)
:done
:: add matching localization files needed for cmd.exe
MKDIR "%current_file_path%\CMD_exes\%UI_LANG%" > NUL 2>&1
MKDIR "%current_file_path%\CMD_exes\mui_files" > NUL 2>&1
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\mui_files\cmd_1_%program_name%.exe.mui"
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\mui_files\cmd_2_%program_name%.exe.mui"
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\mui_files\cmd_3_%program_name%.exe.mui"
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\mui_files\cmd_4_%program_name%.exe.mui"
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\%UI_LANG%\cmd_1_%program_name%.exe.mui"
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\%UI_LANG%\cmd_2_%program_name%.exe.mui"
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\%UI_LANG%\cmd_3_%program_name%.exe.mui"
COPY /Y "%SystemRoot%\System32\%UI_LANG%\cmd.exe.mui" "%current_file_path%\CMD_exes\%UI_LANG%\cmd_4_%program_name%.exe.mui"
:: ===================

:: create shortcut for starting the program:
call utilities\create_shortcut.bat "%shortcut_destination_path%\%start_name%.lnk" "%current_file_path%\CMD_exes\cmd_1_%program_name%.exe" "/C start_program.bat ''%settings_path%''"  "%current_file_path%" "%icon_path%" "PyApp-Template"
:: create a shortcut for the settings.yaml file:
call utilities\create_shortcut.bat "%shortcut_destination_path%\%settings_name%.lnk" "%current_file_path%\CMD_exes\cmd_2_%program_name%.exe" "/C START '''' ''%user_settings_path%''"  "%current_file_path%" "%settings_icon_path%" "PyApp-Template"
:: creare shortcut for launcher without terminal and with output to log file:
call utilities\create_shortcut.bat "%shortcut_destination_path%\%start_no_terminal_name%.lnk" "%current_file_path%\CMD_exes\cmd_3_%program_name%.exe" "/C run_batch_with_file_output_and_no_terminal.bat start_program.bat ''%log_path%'' ''%process_id_file_path%.pid'' ''%settings_path%'' nopause"  "%current_file_path%" "%icon_path%" "PyApp-Template"
:: create shortcut for killing the running program:
call utilities\create_shortcut.bat "%shortcut_destination_path%\%stop_no_terminal_name%.lnk" "%current_file_path%\CMD_exes\cmd_4_%program_name%.exe" "/C kill_process_with_id.bat ''%process_id_file_path%''" "%current_file_path%" "%stop_icon_path%" "PyApp-Template"

:: print info, wait for any key and exit:
ECHO:
ECHO: "%start_name%", "%start_no_terminal_name%", "%stop_no_terminal_name%" ^& "%settings_name%" should be now in "%shortcut_destination_path%" if there were no errors. Press any key to exit.
ECHO:
pause > nul
endlocal & EXIT /B %errorlevel%

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
