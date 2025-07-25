@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM make this code local so no variables of a potential calling program are changed:
SETLOCAL

@REM define local variables (do not have spaces before or after the "=" and at the end of the line; do not add comments to the lines; use "\" to separate folder levels; do not put "\" at the end of paths):
SET batch_file_path=%~1

@REM run batch file without terminal
IF NOT "%~4"=="" (
	powershell -Command "Start-Process '%~batch_file_path%' -ArgumentList '%~2', '%~3', '%~4' -WindowStyle Hidden"
) ELSE (
	IF NOT "%~3"=="" (
		powershell -Command "Start-Process '%~batch_file_path%' -ArgumentList '%~2', '%~3' -WindowStyle Hidden"
	) ELSE ( 
		IF NOT "%~2"=="" (
			powershell -Command "Start-Process '%~batch_file_path%' -ArgumentList '%~2' -WindowStyle Hidden"
		) ELSE (
			powershell -Command "Start-Process '%~batch_file_path%' -WindowStyle Hidden"
		)	
	)
)

@REM close program but not a poential program calling this program
EXIT /B

