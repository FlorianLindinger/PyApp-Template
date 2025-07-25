@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM make this code local so no variables of a potential calling program are changed:
SETLOCAL

@REM define local variables (do not have spaces before or after the "=" and at the end of the line; do not add comments to the lines; use "\" to separate folder levels; do not put "\" at the end of paths):
SET batch_file_path=%~1
IF "%~2"=="" (
	SET log_path=log.txt
) ELSE (
	SET log_path=%~2
)

@REM run batch file and redirect print and error output to log_path
IF NOT "%~3"=="" (
	CALL "%~batch_file_path%" "%~3" > "%~log_path%" 2>&1
) ELSE (
	CALL "%~batch_file_path%" > "%~log_path%" 2>&1
)

@REM print output that is in log file also to console
TYPE "%~log_path%"

@REM delete log_path if it is empty, i.e. there were no errors/prints in the batch execution:
FOR /F %%i IN ("%~log_path%") DO SET file_length=%%~zi
IF "%~file_length%"=="0" (
	DEL "%~log_path%"
) 

@REM close program
EXIT /B

