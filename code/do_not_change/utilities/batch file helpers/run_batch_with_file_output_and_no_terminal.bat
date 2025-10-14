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
SET "batch_file_path=%~1"
IF "%~2"=="" (
	SET "log_path=..\..\log.txt"
) ELSE (
	SET "log_path=%~2"
)
IF "%~3"=="" (
	SET "process_id_file_path=..\..\id_of_currently_running_hidden_program.pid"
) ELSE (
	SET "process_id_file_path=%~3"
)

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM put arguments starting from the i-th (from calling this batch file) in the string "args_list" with space in between and each surrouned by " on both sides:
SETLOCAL enabledelayedexpansion
SET args_list=
SET "i=4"
:loop_args
  CALL SET "arg=%%~%i%%"
  IF "%arg%"=="" ( GOTO args_done)
  SET "arg=!arg:"=""!"
  SET args_list=!args_list! "!arg!"
  SET /a i+=1
GOTO loop_args
:args_done

@REM call batch file without terminal and send outputs (including errors) to log_path and create a process id file as long as code is running:
CALL run_batch_with_no_terminal.bat ^
	run_batch_with_file_output.bat ^
	"%process_id_file_path%"  ^
	"%batch_file_path%" ^
	"%log_path%" ^
	%args_list%

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM exit program without closing a potential calling program
EXIT /B 

@REM ############################
@REM --- Function Definitions ---
@REM ############################