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
@REM CAREFUL WITH python_environment_path!
@REM BE VERY CAREFUL WITH THIS PATH: This folder might be deleted if the environment is reset. So do not write something like just ..\..\ which would delete any folder happening to be at that position. Even if you knwo what is at that path, mistakes with relative paths can happen:
SET python_environment_path=..\..\python_environment_code\python_environment
@REM CAREFUL WITH python_environment_path!

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM delete old environment if existing:
IF EXIST "%python_environment_path%\Scripts\activate.bat" (
	RD /S /Q "%python_environment_path%" &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
	IF NOT EXIST "%python_environment_path%\Scripts\activate.bat" (
		ECHO: Successfully deleted the old python environment
		ECHO:
	) ELSE (
		ECHO:
		ECHO: Error: Failed to deleted the old python environment
		ECHO:
		ECHO: Press any key to exit
		PAUSE >NUL 
		EXIT
	)
)

@REM create new environment:
CALL create_local_python_environment.bat %~1 %~2

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