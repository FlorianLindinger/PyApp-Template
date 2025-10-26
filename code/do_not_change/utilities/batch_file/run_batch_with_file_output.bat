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

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM makes python files (if called) flush immediately what they print to the log file
SET "PYTHONUNBUFFERED=1"
@REM utf-8 encoding needed for python output (if called) to avoid errors for special characters
SET "PYTHONIOENCODING=utf-8"

@REM put arguments starting from the third (from calling this batch file) in the string "args_list" with space in between and each surrouned by " on both sides:
SETLOCAL enabledelayedexpansion
SET "args_list="
SET "i=3"
:loop_args
  CALL SET "arg=%%~%i%%"
  IF "%arg%"=="" ( GOTO args_done)
  SET "arg=!arg:"=""!"
  SET args_list=!args_list! "!arg!"
  SET /a i+=1
GOTO loop_args
:args_done

@REM run batch file and redirect print and error output to log_path
CALL "%batch_file_path%" %args_list% > "%log_path%" 2>&1

@REM @REM delete log_path if it is empty, i.e. there were no errors/prints in the batch execution:
@REM IF EXIST "%log_path%" (
@REM     SET "file_length=%~z1"
@REM     FOR %%F IN ("%log_path%") DO SET "file_length=%%~zF"
@REM     IF "%file_length%"=="0" (
@REM         DEL "%log_path%"
@REM     )
@REM )

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM exit program without closing a potential calling program
EXIT /B 

@REM ############################
@REM --- Function Definitions ---
@REM ############################