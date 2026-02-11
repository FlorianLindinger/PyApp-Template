:: ========================
:: --- Code Description ---
:: ========================

:: =========================
:: --- Setup & Variables ---
:: =========================

:: turn off printing of commands and use local variables
@ECHO OFF & SETLOCAL enabledelayedexpansion

:: get current_file_path because it's needed in script and gets potentially chagned by a call
SET "current_file_path=%~dp0"

:: set variables from args or default args:
SET "batch_file_path=%~1"
IF "%~2"=="" (
	SET "log_path=log.txt"
) ELSE (
	SET "log_path=%~2"
)
IF "%~3"=="" (
	SET "process_id_file_path=running_hidden_app_id.pid"
) ELSE (
	SET "process_id_file_path=%~3"
)

:: ======================
:: --- Code Execution ---
:: ======================

:: put arguments starting from the i-th (from calling this batch file) in the string "args_list" with space in between and each surrouned by " on both sides:
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

:: call batch file without terminal and send outputs (including errors) to log_path and create a process id file as long as code is running:
CALL "%current_file_path%run_batch_with_no_terminal.bat" ^
	"%current_file_path%run_batch_with_file_output.bat" ^
	"%process_id_file_path%"  ^
	"%batch_file_path%" ^
	"%log_path%" ^
	%args_list%

:: exit 
EXIT 0