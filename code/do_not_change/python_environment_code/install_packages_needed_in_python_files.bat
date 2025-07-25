@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM define local variables (do not have spaces before or after the "=" and at the end of the line; do not add comments to the lines; use "\" to separate folder levels; do not put "\" at the end of paths):
SET python_env_code_path=..\..\

@REM upgrade pip
python -m pip install --upgrade pip

@REM activate (or create & activate) python environment:
CALL activate_or_create_environment.bat nopause

@REM install globally a package to find required packages in python files
pip install pipreqs

@REM move to folder of python files
CD /D %python_env_code_path%

@REM install needed packages
pipreqs . --force --savepath tmp.txt
pip install --upgrade -r tmp.txt
DEL tmp.txt

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: All needed packages installed if no errors above. Press any key to exit
	PAUSE >NUL 
)