@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM define local variables (do not have spaces before or after the "=" and at the end of the line; do not add comments to the lines; use "\" to separate folder levels; do not put "\" at the end of paths):
SET python_environment_path=..\..\python_environment_code\python_environment

@REM create python environment if not existing:
if not exist "%python_environment_path%\Scripts\activate.bat" (
	call activate_or_create_environment.bat "nopause"
)

@REM upgrade pip
pip install --upgrade pip

@REM print how to install:
ECHO:
ECHO: Write 'pip install {package name}' to install a package in the local environment:
ECHO:

@REM start console with environment:
START /B /LOW /WAIT call "%python_environment_path%\Scripts\activate.bat"

@REM print warning because this code should not be reached:
ECHO:
ECHO: Error: See above
ECHO:
ECHO: Press any key to exit
PAUSE >NUL 
EXIT

