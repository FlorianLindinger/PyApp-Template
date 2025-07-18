@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM activate (or create & activate) python environment:
CALL "activate_or_create_environment.bat" "nopause"

@REM upgrade pip
python -m pip install --upgrade pip

@REM upgrade all packages as far as conflicts allow
pip freeze > tmp.txt
pip install --upgrade -r tmp.txt
DEL tmp.txt

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: All packages upgraded if no errors above. Press any key to exit
	PAUSE >NUL 
)