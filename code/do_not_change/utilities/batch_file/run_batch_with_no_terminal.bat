@REM ########################
@REM --- Code Description ---
@REM ########################

@REM #########################
@REM --- Setup & Variables ---
@REM #########################

:: turn off printing of commands and use local variables
@ECHO OFF & SETLOCAL

@REM move to folder of this file (needed for relative path shortcuts)

rem @REM current_file_path varaible needed as workaround for nieche windows bug where the 
SET "current_file_path=%~dp0"
rem CD /D "%current_file_path%"

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET "batch_file_path=%~1"
IF "%~2"=="" (
	SET "process_id_file_path=id_of_currently_running_hidden_program.pid"
) ELSE (
	SET "process_id_file_path=%~2"
)

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM append all arguments to %args% encoded i.e., spaces as __SPC__:
CALL :AppendEncoded args "%batch_file_path%"
CALL :AppendEncoded args "%process_id_file_path%"

@REM append any remaining args starting from with i-th:
SET "i=3"
:shift_more
IF %i% LEQ 1 GOTO done_shifting
SHIFT
SET /a i-=1
GOTO shift_more
:done_shifting
:append_more
  IF "%~1"=="" GOTO end_append
  CALL :AppendEncoded args "%~1"
  SHIFT
  GOTO append_more
:end_append

@REM call batch_file_path with arguments in hidden terminal and write the process ID of the hidden program to process_id_file_path. This file gets deleted when the code ends or if it is killed with kill_process_with_id.bat:
POWERSHELL -Command "$p = Start-Process '%current_file_path%helper_run_batch_with_no_terminal.bat' -ArgumentList %args% -WindowStyle Hidden -PassThru; [System.IO.File]::WriteAllText('%process_id_file_path%',$p.Id)"

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM exit program without closing a potential calling program
EXIT /B 0

@REM ############################
@REM --- Function Definitions ---
@REM ############################

@REM -------------------------------------------------
@REM Needed for passing arguemtns to powershell call of batch file: Function to add arguments to variable with spaces encoded as __SPC__. Comma added in between arguments.
@REM -------------------------------------------------
:AppendEncoded
  @REM %1 = variable name to append into (no % around name)
  @REM %2 = raw argument
  SETLOCAL EnableDelayedExpansion
  SET "a=%~2"
  @REM encode spaces with ASCII placeholder
  SET "a=!a: =__SPC__!"
  SET "cur=!%~1!"
  IF DEFINED cur (
    SET "cur=!cur!, "!a!""
  ) ELSE (
    SET "cur="!a!""
  )
  ENDLOCAL & SET "%~1=%cur%"
  EXIT /B

@REM -------------------------------------------------

