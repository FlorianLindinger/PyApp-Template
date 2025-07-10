@REM shortcut_by_OptimumX.exe (original Shortcut.exe from OptimiumX: https://www.optimumx.com/downloads.html#Shortcut) is an exe that allows to modify a shortcut
@REM get help with "generate_shortcut.exe /?"

@REM move to folder with needed code
CD code/other_code

@REM import settings in non-user_settings.ini:
FOR /F "tokens=1,2 delims==" %%a IN ('findstr "^" "non-user_settings.ini"') DO (set "%%a=%%b")

@REM The following line generates a shortcut with specific "target","start in" which is needed for the abiltiy to add to taskbar. These shortcuts need absolute paths which don't transfer correctly via GIT. GIT can have relative shortcut path which then would not allow even for the starting shortcut to be moved out of the folder. Moreover manually generated default shortcuts also can't be added to the taskbar. The icon is also added at this opportunity.:
call shortcut_by_OptimumX.exe /F:"%program_name%.lnk" /A:C /T:"cmd.exe" /P:"/k start.bat" /I:"%~dp0code/other_code/icon.ico" /W:"%~dp0code/other_code"

@REM Move shortcut result back to where this file was called
move "%program_name%.lnk" "..\.."
