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

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM If present: decode to spaces back from the "__SPC__" placeholder and combine arguements after the first 2 together into args_list
SET "batch_file_path=%~1"
SET "batch_file_path=%batch_file_path:__SPC__= %"
SET "file_path=%~2"
SET "file_path=%file_path:__SPC__= %"
@REM shift them out
SHIFT
SHIFT
SETLOCAL EnableDelayedExpansion
SET "args_list="
:next_arg
IF "%~1"=="" GOTO done
    SET "a=%~1"
    SET "a=%a:__SPC__= %"
    SET "args_list=!args_list! "%a%""
    SHIFT
GOTO next_arg
:done

@REM run program with arguments
CALL "%batch_file_path%" %args_list%

@REM delete file
IF EXIST "%file_path%" IF NOT EXIST "%file_path%\" (
    DEL "%file_path%"
)

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM exit program without closing a potential calling program
EXIT /B 

@REM ############################
@REM --- Function Definitions ---
@REM ############################