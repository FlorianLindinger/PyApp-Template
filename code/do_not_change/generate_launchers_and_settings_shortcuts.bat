@REM ###################################
@REM --- Code Description & Comments ---
@REM ###################################

@REM "@REM" indicates the start of a comment (use "&@REM" for comments at the end of a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM #########################
@REM --- Setup & Variables ---
@REM #########################

@REM turn off printing of commands:
@ECHO OFF

@REM make this code local so no variables of a potential calling program are changed:
SETLOCAL

@REM move to folder of this file (needed for relative path shortcuts)
@REM current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET current_file_path=%~dp0
CD /D "%current_file_path%"

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value). Add inline comments therefore without a space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths):
SET non_user_settings_path=..\non-user_settings.ini
SET icon_path=..\icons\icon.ico
SET settings_icon_path=..\icons\settings_icon.ico
SET user_settings_path=..
SET shortcut_destination_path=..\..
SET log_path=..\..\log.txt

@REM import settings from settings_path (e.g., for importing parameter "example" add the line within the last round brackets below "IF %%a==example (SET example=%%b)"):
FOR /F "tokens=1,2 delims==" %%a IN ("%non_user_settings_path%") DO (
	IF %%a==program_name (SET program_name=%%b)
)

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
CALL shortcut_by_OptimumX.exe /F:"%program_name%.lnk" /A:C /T:"cmd.exe" /P:"/K start_program.bat" /I:"%~dp0%icon_path%" /W:"%~dp0

@REM also create a shortcut for the settings.yaml file
IF "%user_settings_path%"=="" ( @REM shortcut.exe somehow does not need a closing " if the path after /W ends with \
	CALL shortcut_by_OptimumX.exe /F:"%program_name%_settings.lnk" /A:C /T:"cmd.exe" /P:"/C START settings.yaml" /I:"%~dp0%settings_icon_path%" /W:"%~dp0
) ELSE (
	CALL shortcut_by_OptimumX.exe /F:"%program_name%_settings.lnk" /A:C /T:"cmd.exe" /P:"/C START settings.yaml" /I:"%~dp0%settings_icon_path%" /W:"%~dp0%user_settings_path%"
)

@REM also creare shortcut for launcher without terminal and with output to log file
CALL shortcut_by_OptimumX.exe /F:"%program_name% (with log & no terminal).lnk" /A:C /T:"cmd.exe" /P:"/C run_batch_with_file_output_and_no_terminal.bat start_program.bat '%log_path%' nopause" /I:"%~dp0%icon_path%" /W:"%~dp0 

@REM move shortcut results back to destination 
ECHO:
MOVE "%program_name%.lnk" "%~dp0%shortcut_destination_path%"
MOVE "%program_name%_settings.lnk" "%~dp0%shortcut_destination_path%"
MOVE "%program_name% (with log & no terminal).lnk" "%~dp0%shortcut_destination_path%"

@REM print info:
CALL :make_absolute_path_if_relative "%~dp0%shortcut_destination_path%"
ECHO:
ECHO: "%program_name%","%program_name% (with log & no terminal)" ^& "%program_name%_settings" should be now in "%OUTPUT%" if there were no errors
ECHO:

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM pause if not called by other script with "nopause" as last argument:
FOR %%a IN (%*) DO SET last_argument=%%a
IF NOT "%last_argument%"=="nopause" (
	ECHO: Press any key to exit
	PAUSE >NUL 
)

@REM Exit program without closing a potential calling program
EXIT /B 

@REM ############################
@REM --- Function Definitions ---
@REM ############################

@REM function that makes path to absolute if not already
:make_absolute_path_if_relative
	SET OUTPUT=%~f1
	EXIT /B