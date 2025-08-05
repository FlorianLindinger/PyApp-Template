@REM ###################################
@REM --- Code Description & Comments ---
@REM ###################################

@REM "@REM" indicates the start of a comment (use "&@REM" for comments at the end of a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM #########################
@REM --- Setup & Variables ---
@REM #########################

@REM turn off printing of commands:
@ECHO OFF

@REM this code can't use SETLOCAL to not overwrite global variables because the python environment activation won't work then. Therefore the local variables use unlikely labels:

@REM move to folder of this file (needed for relative path shortcuts)
@REM current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path_aoce=%~dp0"
CD /D "%current_file_path_aoce%"

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET "python_environment_path_aoce=..\..\python_environment_code\python_environment"

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM create python environment if not existing:
IF NOT EXIST "%python_environment_path_aoce%\Scripts\activate.bat" (	
	ECHO Creating local python environment for first execution
	ECHO:
	CALL create_local_python_environment.bat "nopause"
)

@REM activate python environment:
CALL "%python_environment_path_aoce%\Scripts\activate.bat"

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