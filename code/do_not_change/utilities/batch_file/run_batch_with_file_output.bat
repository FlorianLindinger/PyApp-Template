:: ========================
:: --- Code Description ---
:: ========================

:: =========================
:: --- Setup & Variables ---
:: =========================

:: turn off printing of commands and use local variables
@ECHO OFF & SETLOCAL enabledelayedexpansion

:: set variables from args or default args:
SET "batch_file_path=%~1"
IF "%~2"=="" (
	SET "log_path=log.txt"
) ELSE (
	SET "log_path=%~2"
)

:: ======================
:: --- Code Execution ---
:: ======================

:: makes python files (if called) flush immediately what they print to the log file
SET "PYTHONUNBUFFERED=1"
:: utf-8 encoding needed for python output (if called) to avoid errors for special characters
SET "PYTHONIOENCODING=utf-8"

:: put arguments starting from the third (from calling this batch file) in the string "args_list" with space in between and each surrouned by " on both sides:
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

:: run batch file and redirect print and error output to log_path
CALL "%batch_file_path%" %args_list% > "%log_path%" 2>&1

:: exit program without closing a potential calling program
EXIT /B 0

