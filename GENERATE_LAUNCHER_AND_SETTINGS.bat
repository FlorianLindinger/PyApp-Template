@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM define local variables
SET non_user_settings_path=..\non-user_settings.ini
SET icon_path=..\icon.ico
SET settings_icon_path=..\settings_icon.ico
SET shortcut_exe_path=..\do_not_change 
SET start_program_path=..\do_not_change &@REM without "\" at end
SET user_settings_path=.. &@REM without "\" at end
SET shortcut_destination_path=..\..\

@REM import settings:
FOR /F "tokens=1,2 delims==" %%a IN (%non_user_settings_path%) DO (
	IF %%a==program_name (SET program_name=%%b)
)

@REM move to folder of shortcut_exe
CD %shortcut_exe_path%

@REM shortcut_by_OptimumX.exe (original Shortcut.exe from OptimiumX: https://www.optimumx.com/downloads.html#Shortcut) is an exe that allows to modify a shortcut
@REM get help with "generate_shortcut.exe /?"
@REM The following line generates a shortcut with specific "target","start in" which is needed for the abiltiy to add to taskbar. These shortcuts need absolute paths which don't transfer correctly via GIT. GIT can have relative shortcut path which then would not allow even for the starting shortcut to be moved out of the folder. Moreover manually generated default shortcuts also can't be added to the taskbar. The icon is also added at this opportunity.:
IF "%start_program_path%"=="" ( @REM somehow the /W: option does not need a closing " if only "%~dp0 is chosen (maybe becasue of escape character \ at end of %~dp0).
	CALL shortcut_by_OptimumX.exe /F:"%program_name%.lnk" /A:C /T:"cmd.exe" /P:"/K start_program.bat" /I:"%~dp0%icon_path%" /W:"%~dp0
) ELSE (
	CALL shortcut_by_OptimumX.exe /F:"%program_name%.lnk" /A:C /T:"cmd.exe" /P:"/K start_program.bat" /I:"%~dp0%icon_path%" /W:"%~dp0%start_program_path%"
)
@REM also create a shortcut for the settings.yaml file for the same reasons
IF "%user_settings_path%"=="" ( 
	CALL shortcut_by_OptimumX.exe /F:"%program_name%_settings.lnk" /A:C /T:"cmd.exe" /P:"/C START settings.yaml" /I:"%~dp0%settings_icon_path%" /W:"%~dp0
) ELSE (
	CALL shortcut_by_OptimumX.exe /F:"%program_name%_settings.lnk" /A:C /T:"cmd.exe" /P:"/C START settings.yaml" /I:"%~dp0%settings_icon_path%" /W:"%~dp0%user_settings_path%"
)

@REM move shortcut results back to destination 
ECHO:
MOVE "%program_name%.lnk" "%~dp0%shortcut_destination_path%"
MOVE "%program_name%_settings.lnk" "%~dp0%shortcut_destination_path%"

@REM print info:
ECHO:
ECHO: "%program_name%" and "%program_name%_settings" should be now in "%~dp0%shortcut_destination_path%"
ECHO:

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: Press any key to exit
	PAUSE >NUL 
)
