@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM define local variables (do not have spaces before or after the "="" and at the end of the line; do not add comments to the lines; use "\" to separate folder levels; do not put "\" at the end of paths):
SET log_path=..\..\log_start_errors.txt

@REM run starting batch file without terminal that prints to a log and sends its errors to log_path
powershell -WindowStyle Hidden -Command "Start-Process start_program_with_log_file_and_no_terminl.bat 2>'%log_path%' -WindowStyle Hidden"

@REM delete log_path if it is empty i.e. there were no errors in the batch execution
Setlocal EnableDelayedExpansion
SET "cmd=findstr /R /N "^^" '%log_path%' | FIND /C ":""
for /f %%a in ('!cmd!') DO SET file_length=%%a
if "%file_length%"=="0" (
	del %log_path%
) 

@REM close program
EXIT

