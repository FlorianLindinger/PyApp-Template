@REM ########################
@REM --- Code Description ---
@REM ########################

@REM #########################

@REM turn off printing of commands and make variables local
@ECHO OFF & SETLOCAL

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

mkdir 1

@REM delete file
IF EXIST "%file_path%" (
    IF NOT EXIST "%file_path%\" (
        DEL "%file_path%"
    )
) 

:: exit 
EXIT /B 0

