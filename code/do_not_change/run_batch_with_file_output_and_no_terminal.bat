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
SET batch_file_path=%~1
IF "%~2"=="" (
	SET log_path=log.txt
) ELSE (
	SET log_path=%~2
)

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM call batch file without terminal and send outputs (including errors) to log_path
CALL run_batch_with_no_terminal.bat run_batch_with_file_output.bat "%batch_file_path%" "%log_path%" "%~3"

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM pause if not called by other script with "nopause" as last argument:
FOR %%a IN (%*) DO SET last_argument=%%a
IF NOT "%last_argument%"=="nopause" (
	ECHO: Press any key to exit
	PAUSE >NUL 
)

@REM Exit program without closing a potential calling program
EXIT /B 

@REM ############################
@REM --- Function Definitions ---
@REM ############################