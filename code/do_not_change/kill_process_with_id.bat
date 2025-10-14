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
@REM for extra safety to not delete files: The file (if no number) is mandated to be .pid and must not be included in the path:
SET "process_id_or_file=%~1"

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM get process id if it input is a file containing it
IF EXIST "%process_id_or_file%.pid" (
	SET /p PID=<"%process_id_or_file%.pid"
) ELSE (
	CALL :is_integer "%process_id_or_file%"
	IF "%OUTPUT%"=="1" (
		SET "PID=%process_id_or_file%"
	) ELSE (
		ECHO: Warning: File "%process_id_or_file%.pid" does not exist. ^(don't include the file ending in the argument^). 
		ECHO: Press any key to exit
		PAUSE >NUL 
		EXIT /B
	)
)

@REM kill process with process ID PID and its child processes:
TASKKILL /PID %PID% /T /F

IF EXIST "%process_id_or_file%.pid" (
	DEL "%process_id_or_file%.pid"
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

SETLOCAL enabledelayedexpansion
:is_integer
SET "val=%~1"
ECHO %val% | FINDSTR /R "^[0-9][0-9]*$" >NUL
IF %ERRORLEVEL%==0 (
	SET "OUTPUT=1"
) ELSE (
	SET "OUTPUT=0"
)
EXIT /B