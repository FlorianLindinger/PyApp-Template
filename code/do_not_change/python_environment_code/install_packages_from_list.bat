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

@REM define packages_list_path as first argument when calling this file (requirements.txt if not given):
SET "packages_list_path=%~1"
IF "%packages_list_path%"=="" (
	SET "packages_list_path=requirements.txt"
)

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM make packages_list_path to absolute path:
CALL :make_absolute_path_if_relative "%packages_list_path%"
SET "packages_list_path=%OUTPUT%"

@REM install packages from file or warn if it does not exist and abort:
IF EXIST "%packages_list_path%" (
	pip install -r "%packages_list_path%" --disable-pip-version-check
) ELSE (
	ECHO: Error: "%packages_list_path%" does not exist. Program aborted: Press any key to exit
	PAUSE >NUL 
	EXIT
)

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