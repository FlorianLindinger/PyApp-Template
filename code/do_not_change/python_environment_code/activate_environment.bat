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

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET "path_to_activate_file=%~1"

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM abort if not existing or defined and warn:
IF "%path_to_activate_file%"=="" (
	ECHO: Error: Need to define path to activate.bat as first argument when calling activate_environment.bat. Program aborted: Press any key to exit
	PAUSE > NUL
	EXIT
)
IF NOT EXIST "%path_to_activate_file%" (
	CALL :make_absolute_path_if_relative "%path_to_activate_file%"
	ECHO: Error: Defined path to activate.bat ("%OUTPUT%"^) as first argument when calling activate_environment.bat does not exist. Program aborted: Press any key to exit
	PAUSE > NUL
	EXIT
)

@REM activate environment
CALL "%python_environment_path%\Scripts\activate.bat"

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

@REM -------------------------------------------------
@REM function that makes relative path (relative to current working directory) to absolute if not already:
@REM -------------------------------------------------
:make_absolute_path_if_relative
	SET "OUTPUT=%~f1"
	GOTO :EOF
@REM -------------------------------------------------