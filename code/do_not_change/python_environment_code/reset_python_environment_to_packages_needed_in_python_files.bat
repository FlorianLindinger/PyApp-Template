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
SET python_code_path=..\..
SET python_environment_path=..\..\python_environment_code\python_environment

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM upgrade pip
python -m pip install --upgrade pip

@REM install globally a package to find required packages in python files
pip install pipreqs

@REM activate (or create & activate) python environment:
CALL activate_or_create_environment.bat nopause

@REM replace default_python_packages file with needed packages
pipreqs "%python_code_path%" --force --savepath tmp.txt --ignore "%python_environment_path%"

@REM reset python environment with only required packages
CALL reset_python_environment.bat tmp.txt nopause

@REM remove temporary file that lists needed packages
DEL tmp.txt 

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM pause if not called by other script with "nopause" as last argument:
SET last_argument=
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