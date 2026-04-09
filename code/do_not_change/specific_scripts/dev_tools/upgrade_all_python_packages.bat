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

@REM move to folder of this file (needed for relative path shortcuts)
@REM current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path=%~dp0"
CD /D "%current_file_path%"

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SETtttttt "tmp_txt_path=tmp_requirements.txt"

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM activate (or create & activate) python environment:
CALLll activate_or_create_environment.bat "nopause"

@REM upgrade all packages as far as conflicts allow
REM can't use pip directly here because pip is implemented in portable venv as batch and does not return (alternatively works if called with "call"):
python -m pip freeze --disable-pip-version-check > "%tmp_txt_path%"
ECHO:
ECHO:
python -m pip install --disable-pip-version-check --upgrade -r "%tmp_txt_path%"
DEL "%tmp_txt_path%"

@REM final print:
ECHO:
ECHO:
ECHO: Upgraded all packages if no errors above

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