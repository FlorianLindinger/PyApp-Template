@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM define local variables (do not have spaces before or after the = and at the end of the line):
SET default_packages_file_path=..\..\default_python_packages.txt

@REM activate environment:
CALL "activate_or_create_environment.bat" "nopause"

@REM print warning if requirements.txt already exists:
IF exist %default_packages_file_path% (
    ECHO "%~dp0%default_packages_file_path%" already exists and will be overwritten
	ECHO:
)

@REM upgrade pip
pip install --upgrade pip

@REM generate requirements.txt:
pip freeze > %default_packages_file_path%

@REM print
ECHO: Generated "%~dp0%default_packages_file_path%"

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: Press any key to exit
	PAUSE >NUL
)