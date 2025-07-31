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

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET python_code_path=..\..
SET python_environment_path=..\..\python_environment_code\python_environment
SET temporary_txt_path=..\..\..\tmp.txt

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM upgrade pip
python -m pip install --upgrade pip > NUL 

@REM install globally a package to find required packages in python files
pip install pipreqs > NUL

@REM activate (or create & activate) python environment:
CALL activate_or_create_environment.bat "nopause"

@REM get list of needed packages
pipreqs "%python_code_path%" --force --savepath "%temporary_txt_path%" --ignore "%python_environment_path%"
ECHO:
ECHO:
ECHO:

@REM install list of needed packages
pip install --upgrade -r "%temporary_txt_path%"

@REM remove temporary file that lists needed packages
DEL "%temporary_txt_path%"

@REM print final message
ECHO:
ECHO:
ECHO:
ECHO: Everything needed in the python files should be installed now if no errors above.

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