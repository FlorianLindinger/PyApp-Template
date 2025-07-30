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
SET python_environment_path=..\..\python_environment_code\python_environment

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM create python environment if not existing:
IF NOT EXIST "%python_environment_path%\Scripts\activate.bat" (
	CALL activate_or_create_environment.bat "nopause"
)

@REM upgrade pip
pip install --upgrade pip

@REM print how to install:
ECHO:
ECHO: Write 'pip install {package name}' to install a package in the local environment:
ECHO:

@REM start console with environment:
START /B /LOW /WAIT CALL "%python_environment_path%\Scripts\activate.bat"

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM print warning because this code should not be reached:
ECHO:
ECHO: Error (See above)! Press any key to exit
PAUSE >NUL 
EXIT

@REM ############################
@REM --- Function Definitions ---
@REM ############################
