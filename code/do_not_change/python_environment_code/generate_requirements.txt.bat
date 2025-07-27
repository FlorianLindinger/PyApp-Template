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
SET default_packages_file_path=..\..\python_environment_code\default_python_packages.txt

@REM import settings from settings_path (e.g., for importing parameter "example" add the line within the last round brackets below "IF %%a==example (SET example=%%b)"):
FOR /F "tokens=1,2 delims==" %%a IN (%settings_path%) DO (
)

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM upgrade pip
python -m pip install --upgrade pip

@REM activate environment:
CALL activate_or_create_environment.bat nopause

@REM print warning if requirements.txt already exists:
IF exist "%default_packages_file_path%" (
    ECHO "%current_file_path%%default_packages_file_path%" already exists and will be overwritten
	ECHO:
)

@REM generate requirements.txt:
python -m pip freeze > "%default_packages_file_path%"

@REM print message:
CALL make_absolute_path_if_relative: "%current_file_path%%default_packages_file_path%"
ECHO: Generated "%OUTPUT%"

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM pause if not called by other script with "nopause" as last argument:
FOR %%a IN (%*) DO SET last_argument=%%a
IF NOT "%last_argument%"=="nopause" (
	ECHO: Press any key to exit
	PAUSE >NUL 
)

@REM exit program without closing a potential calling program
EXIT /B 

@REM ############################
@REM --- Function Definitions ---
@REM ############################

@REM function that makes path to absolute if not already. Access as %OUTPUT% (also gets rid of unresolved ".." in path):
:make_absolute_path_if_relative
	SET OUTPUT=%~f1
	EXIT /B