@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD "%~dp0"

@REM activate environment:
CALL "activate_or_create_environment.bat" "nopause"

@REM print warning if requirements.txt already exists:
IF exist requirements.txt (
    ECHO requirements.txt already exists and will be overwritten
)

@REM generate requirements.txt:
pip freeze > requirements.txt

@REM print
ECHO: Generated requirements.txt in "%~dp0"

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: Press any key to exit
	PAUSE >NUL 
	ECHO:
)