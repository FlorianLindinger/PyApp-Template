@REM ###################################
@REM --- Code Description & Comments ---
@REM ###################################

@REM Note: "@REM" indicates the start of a comment (use "&@REM" for comments at the end of a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM #########################
@REM --- Setup & Variables ---
@REM #########################

@REM turn off printing of commands:
@ECHO OFF

@REM make this code local so no variables of a potential calling program are changed:
SETLOCAL

@REM import settings from settings_path:
SET "settings_path=..\non-user_settings.ini"
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( SET "%%A=%%B" )

@REM move to folder of this file (needed for relative path shortcuts)
@REM current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path=%~dp0"
CD /D "%current_file_path%"

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET "non_user_settings_path=..\non-user_settings.ini"
SET "icon_path=..\icons\icon.ico"
SET "settings_icon_path=..\icons\settings_icon.ico"
SET "stop_icon_path=..\icons\stop.ico"
SET "user_settings_path=.."
SET "shortcut_destination_path=..\.."
SET "log_path=..\..\log.txt"
@REM: For safety, the file ending (.pid) must not be included in process_id_file_path (see kill_process_with_id.bat):
SET "process_id_file_path=..\..\id_of_currently_running_hidden_program"

SET "start_name=%program_name%"
SET "start_no_terminal_name=%program_name% (with log & no terminal)"
SET "settings_name=%program_name% - settings"
SET "stop_no_terminal_name=stop (no-terminal) %program_name%"

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM shortcut_by_OptimumX.exe (original Shortcut.exe from OptimiumX: https://www.optimumx.com/downloads.html#Shortcut)
@REM is an exe that allows to modify/create a shortcut without admin rights.
@REM Get help with "shortcut_by_OptimumX.exe /?".
@REM The following line generates a shortcut with specific "target","start in" which is needed for the abiltiy to add 
@REM to taskbar. These shortcuts need absolute paths which don't transfer correctly via GIT. GIT can have relative 
@REM shortcut path which then would not allow even for the starting shortcut to be moved out of the folder. Moreover 
@REM manually generated default shortcuts also can't be added to the taskbar. The icon is also added at this opportunity:
CALL shortcut_by_OptimumX.exe /F:"%start_name%.lnk" /A:C /T:"cmd.exe" /P:"/C start_program.bat" /I:"%current_file_path%%icon_path%" /W:"%current_file_path%

@REM create a shortcut for the settings.yaml file
IF "%user_settings_path%"=="" ( @REM shortcut.exe somehow does not need a closing " if the path after /W ends with \
	CALL shortcut_by_OptimumX.exe /F:"%settings_name%.lnk" /A:C /T:"cmd.exe" /P:"/C START settings.yaml" /I:"%current_file_path%%settings_icon_path%" /W:"%current_file_path%
) ELSE (
	CALL shortcut_by_OptimumX.exe /F:"%settings_name%.lnk" /A:C /T:"cmd.exe" /P:"/C START settings.yaml" /I:"%current_file_path%%settings_icon_path%" /W:"%current_file_path%%user_settings_path%"
)

@REM creare shortcut for launcher without terminal and with output to log file
CALL shortcut_by_OptimumX.exe /F:"%start_no_terminal_name%.lnk" /A:C /T:"cmd.exe" /P:"/C run_batch_with_file_output_and_no_terminal.bat start_program.bat ""%log_path%"" ""%process_id_file_path%.pid"" nopause" /I:"%current_file_path%%icon_path%" /W:"%current_file_path%

@REM create shortcut for killing the running program
CALL shortcut_by_OptimumX.exe /F:"%stop_no_terminal_name%.lnk" /A:C /T:"cmd.exe" /P:"/C kill_process_with_id.bat ""%process_id_file_path%"" " /I:"%current_file_path%%stop_icon_path%" /W:"%current_file_path%

@REM move shortcut results back to destination 
ECHO:
MOVE "%start_name%.lnk" "%current_file_path%%shortcut_destination_path%"
MOVE "%settings_name%.lnk" "%current_file_path%%shortcut_destination_path%"
MOVE "%start_no_terminal_name%.lnk" "%current_file_path%%shortcut_destination_path%"
MOVE "%stop_no_terminal_name%.lnk" "%current_file_path%%shortcut_destination_path%"

@REM print info:
CALL :make_absolute_path_if_relative "%current_file_path%%shortcut_destination_path%"
ECHO:
ECHO: "%start_name%", "%start_no_terminal_name%", "%stop_no_terminal_name%" ^& "%settings_name%" should be now in "%OUTPUT%" if there were no errors
ECHO:

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM pause if not called by other script with any argument:
IF "%~1"=="" (
	ECHO: Press any key to exit
	PAUSE >NUL 
)

@REM exit program without closing a potential calling program
EXIT /B 

@REM ############################
@REM --- Function Definitions ---
@REM ############################

@REM function that makes path to absolute if not already
:make_absolute_path_if_relative
	SET "OUTPUT=%~f1"
	EXIT /B