@REM ########################
@REM --- Code Description ---
@REM ########################

@REM #########################
@REM --- Setup & Variables ---
@REM #########################

@REM turn off printing of commands:
@ECHO OFF

@REM make this code local so no variables of a potential calling program are changed:
SETLOCAL

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET "settings_path=%~1"

@REM move to folder of this file (needed for relative path shortcuts)
@REM current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path=%~dp0"
CD /D "%current_file_path%"

@REM import settings from settings_path:
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( SET "%%A=%%B" )

@REM convert the path settings that are relative to settings file to absolute paths:
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

@REM needed for interpretation of !program_name! in settings values as value of variable "program_name":
SETLOCAL ENABLEDELAYEDEXPANSION

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM one need multiple copies of windows cmd.exe in order to have multiple cmd shortcuts in the taskbar. We use cmd shortcuts which enables shortcuts to batch files at taskbar in the first place and enables icons:
MKDIR CMD_exes
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_1_%program_name%.exe"
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_2_%program_name%.exe"
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_3_%program_name%.exe"
COPY /Y "%SystemRoot%\System32\cmd.exe" "%current_file_path%\CMD_exes\cmd_4_%program_name%.exe"

@REM shortcut_by_OptimumX.exe (original Shortcut.exe from OptimiumX: https://www.optimumx.com/downloads.html#Shortcut)
@REM is an exe that allows to modify/create a shortcut without admin rights.
@REM Get help with "shortcut_by_OptimumX.exe /?".
@REM The following line generates a shortcut with specific "target","start in" which is needed for the abiltiy to add 
@REM to taskbar. These shortcuts need absolute paths which don't transfer correctly via GIT. GIT can have relative 
@REM shortcut path which then would not allow even for the starting shortcut to be moved out of the folder. Moreover 
@REM manually generated default shortcuts also can't be added to the taskbar. The icon is also added at this opportunity:

@REM create shortcut for starting the program
CALL shortcut_by_OptimumX.exe /F:"%shortcut_destination_path%\%start_name%.lnk" /A:C /T:"%current_file_path%\CMD_exes\cmd_1_%program_name%.exe" /P:"/C start_program.bat ""%settings_path%""" /I:"%icon_path%" /W:"%current_file_path%

@REM create a shortcut for the settings.yaml file
CALL shortcut_by_OptimumX.exe /F:"%shortcut_destination_path%\%settings_name%.lnk" /A:C /T:"%current_file_path%\CMD_exes\cmd_2_%program_name%.exe" /P:"/C START """" ""%user_settings_path%""" /I:"%settings_icon_path%"

@REM creare shortcut for launcher without terminal and with output to log file
CALL shortcut_by_OptimumX.exe /F:"%shortcut_destination_path%\%start_no_terminal_name%.lnk" /A:C /T:"%current_file_path%\CMD_exes\cmd_3_%program_name%.exe" /P:"/C run_batch_with_file_output_and_no_terminal.bat start_program.bat ""%log_path%"" ""%process_id_file_path%.pid"" ""%settings_path%"" nopause" /I:"%icon_path%" /W:"%current_file_path%

@REM create shortcut for killing the running program
CALL shortcut_by_OptimumX.exe /F:"%shortcut_destination_path%\%stop_no_terminal_name%.lnk" /A:C /T:"%current_file_path%\CMD_exes\cmd_4_%program_name%.exe" /P:"/C kill_process_with_id.bat ""%process_id_file_path%"" " /I:"%stop_icon_path%" /W:"%current_file_path%

@REM print info:
ECHO:
ECHO: "%start_name%", "%start_no_terminal_name%", "%stop_no_terminal_name%" ^& "%settings_name%" should be now in "%shortcut_destination_path%" if there were no errors
ECHO:

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM pause if not called by other script with multiple arguments:
IF "%~2"=="" (
	ECHO: Press any key to exit
	PAUSE >NUL 
)

@REM exit program without closing a potential calling program
EXIT /B 

@REM ############################
@REM --- Function Definitions ---
@REM ############################

@REM -------------------------------------------------
@REM function that makes relative path (relative to current working directory) to absolute if not already:
@REM -------------------------------------------------
:make_absolute_path_if_relative
	SET "OUTPUT=%~f1"
	GOTO :EOF

@REM -------------------------------------------------


