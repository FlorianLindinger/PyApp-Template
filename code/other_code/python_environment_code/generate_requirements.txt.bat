@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM activate environment:
CALL "activate_or_create_environment.bat" "nopause"

@REM print warning if requirements.txt already exists:
IF exist requirements.txt (
    ECHO requirements.txt already exists and will be overwritten
)

@REM generate requirements.txt:
pip freeze > requirements.txt

@REM print
ECHO: Generated requirements.txt in current folder

@REM pause if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	PAUSE
	ECHO:
)