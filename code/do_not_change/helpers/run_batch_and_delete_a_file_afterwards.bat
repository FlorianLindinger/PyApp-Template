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

@REM Do not move to folder of this file such that arguement relative paths are with respect to caller

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET batch_file_path=%~1
SET file_path=%~2

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM put arguments starting from the i-th (from calling this batch file) in the string "args_list" with space in between and each surrouned by " on both sides:
SETLOCAL enabledelayedexpansion
SET args_list=
SET i=3
:loop_args
  CALL SET "arg=%%~%i%%"
  IF "%arg%"=="" ( GOTO args_done)
  SET "arg=!arg:"=""!"
  SET args_list=!args_list! "!arg!"
  SET /a i+=1
GOTO loop_args
:args_done

@REM run program with arguments
CALL "%batch_file_path%" %args_list%

@REM delete file
DEL "%file_path%"

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