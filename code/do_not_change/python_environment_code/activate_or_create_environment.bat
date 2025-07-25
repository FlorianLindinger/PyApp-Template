@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM make this code local so no variables of a potential calling program are changed:
SETLOCAL

@REM define local variables (do not have spaces before or after the "=" and at the end of the line; do not add comments to the lines; use "\" to separate folder levels; do not put "\" at the end of paths):
SET python_environment_path=..\..\python_environment_code\python_environment

@REM create python environment if not existing:
IF NOT EXIST "%~python_environment_path%\Scripts\activate.bat" (	
	ECHO Creating local python environment for first execution
	ECHO:
	@ECHO ON
	CALL create_local_python_environment.bat "nopause"
	@ECHO OFF	
)

@REM activate python environment:
CALL "%~python_environment_path%\Scripts\activate.bat"

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: Press any key to exit
	PAUSE >NUL 
)