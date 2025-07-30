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
	SET process_id_file_path=..\..\running_hidden_program_id.pid
) ELSE (
	SET process_id_file_path=%~2
)

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM put arguments starting from the i-th (from calling this batch file) in the string "args_list" with commas in between and each surrouned by \" on both sides and a comma at the start if there is at least one element:
SETLOCAL enabledelayedexpansion
SET args_list=
SET i=3
:loop_args
  CALL SET "arg=%%~%i%%"
  IF "%arg%"=="" ( GOTO args_done)
  IF NOT "%i%"=="2" ( SET "args_list=!args_list!,")
  SET "arg=!arg:"=""!"
  SET "args_list=!args_list! '!arg!'"
  SET /a i+=1
GOTO loop_args
:args_done

@REM call batch_file_path with arguments in hidden terminal and write the process ID of the hidden program to process_id_file_path. This file gets deleted when the code ends or if it is killed with kill_process_with_id.bat:
powershell -Command "$p = Start-Process 'helpers\run_batch_and_delete_a_file_afterwards' -ArgumentList '%batch_file_path%','%process_id_file_path%' %args_list% -WindowStyle Hidden -PassThru; [System.IO.File]::WriteAllText('%process_id_file_path%',$p.Id)"

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