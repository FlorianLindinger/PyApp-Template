@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0" &@REM /D is needed to change drive if necessary

@REM define local variables (do not have spaces before or after the "=" and at the end of the line; do not add comments to the lines; use "\" to separate folder levels; do not put "\" at the end of paths):
SET non_user_settings_path=..\non-user_settings.ini
SET icon_path=..\icons\icon.ico
SET settings_icon_path=..\icons\settings_icon.ico
SET user_settings_path=..
SET shortcut_destination_path=..\..

@REM import settings:
FOR /F "tokens=1,2 delims==" %%a IN (%non_user_settings_path%) DO (
	IF %%a==program_name (SET program_name=%%b)
)

@REM shortcut_by_OptimumX.exe (original Shortcut.exe from OptimiumX: https://www.optimumx.com/downloads.html#Shortcut)
@REM is an exe that allows to modify/create a shortcut without admin rights
@REM get help with "generate_shortcut.exe /?".
@REM The following line generates a shortcut with specific "target","start in" which is needed for the abiltiy to add 
@REM to taskbar. These shortcuts need absolute paths which don't transfer correctly via GIT. GIT can have relative 
@REM shortcut path which then would not allow even for the starting shortcut to be moved out of the folder. Moreover 
@REM manually generated default shortcuts also can't be added to the taskbar. The icon is also added at this opportunity.:
CALL shortcut_by_OptimumX.exe /F:"%program_name%.lnk" /A:C /T:"cmd.exe" /P:"/K start_program.bat" /I:"%~dp0%icon_path%" /W:"%~dp0
@REM also create a shortcut for the settings.yaml file for the same reasons
IF "%user_settings_path%"=="" ( @REM shortcut.exe somehow does not need a closing " if the path after /W ends with \
	CALL shortcut_by_OptimumX.exe /F:"%program_name%_settings.lnk" /A:C /T:"cmd.exe" /P:"/C START settings.yaml" /I:"%~dp0%settings_icon_path%" /W:"%~dp0
) ELSE (
	CALL shortcut_by_OptimumX.exe /F:"%program_name%_settings.lnk" /A:C /T:"cmd.exe" /P:"/C START settings.yaml" /I:"%~dp0%settings_icon_path%" /W:"%~dp0%user_settings_path%"
)
CALL shortcut_by_OptimumX.exe /F:"%program_name% (with log & no terminal).lnk" /A:C /T:"cmd.exe" /P:"/C helper_start_program_with_log_file_and_no_terminl.bat" /I:"%~dp0%icon_path%" /W:"%~dp0

@REM move shortcut results back to destination 
ECHO:
MOVE "%program_name%.lnk" "%~dp0%shortcut_destination_path%"
MOVE "%program_name%_settings.lnk" "%~dp0%shortcut_destination_path%"
MOVE "%program_name% (with log & no terminal).lnk" "%~dp0%shortcut_destination_path%"

@REM print info:
ECHO:
ECHO: "%program_name%","%program_name% (with log & no terminal)" & "%program_name%_settings" should be now in "%~dp0%shortcut_destination_path%" if there were no errors
ECHO:

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: Press any key to exit
	PAUSE >NUL 
)
