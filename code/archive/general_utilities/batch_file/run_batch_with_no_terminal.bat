:: ========================
:: --- Code Description ---
:: ========================

:: =========================
:: --- Setup & Variables ---
:: =========================

:: turn off printing of commands and use local variables:
@ECHO OFF & SETLOCAL enabledelayedexpansion

:: set variables from args or default args:
SET "batch_file_path=%~1"
IF "%~2"=="" (
	SET "process_id_file_path=running_hidden_app_id.pid"
) ELSE (
	SET "process_id_file_path=%~2"
)

:: ======================
:: --- Code Execution ---
:: ======================

:: put arguments starting from the third (from calling this batch file) in the string "args_list" with space in between and each surrouned by ' on both sides and sep  with ,:
SET "i=3"
if "%%~%i%%"=="" ( goto args_done )
CALL SET "args_list='%%~%i%%'"
SET /a i+=1
:loop_args
  CALL SET "arg=%%~%i%%"
  IF "%arg%"=="" ( GOTO args_done)
  SET "arg=!arg:"=""!"
  SET args_list=!args_list!, '!arg!'
  SET /a i+=1
GOTO loop_args
:args_done

:: call batch_file_path with arguments in hidden terminal and write the process ID of the hidden program to process_id_file_path. This file gets deleted when the code ends or if it is killed with kill_process_with_id.bat:
POWERSHELL -Command "$p = Start-Process '%batch_file_path%' -ArgumentList %args_list% -WindowStyle Hidden -PassThru; [System.IO.File]::WriteAllText('%process_id_file_path%',$p.Id); Wait-Process -Id $p.Id; Remove-Item '%process_id_file_path%'"

:: exit program without closing a potential calling program
EXIT /B 0



