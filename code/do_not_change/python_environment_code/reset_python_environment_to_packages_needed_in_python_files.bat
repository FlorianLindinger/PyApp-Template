@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM define local variables (do not have spaces before or after the "=" and at the end of the line; do not add comments to the lines; use "\" to separate folder levels; do not put "\" at the end of paths):
SET python_code_path=..\..
SET default_python_packages_txt_path=..\..\python_environment_code

@REM upgrade pip
python -m pip install --upgrade pip

@REM install globally a package to find required packages in python files
pip install pipreqs

@REM replace default_python_packages file with needed packages
pipreqs "%~python_code_path%" --force --savepath tmp.txt --ignore "%~default_python_packages_txt_path%\python_environment"

@REM reset python environment with only required packages
CALL reset_python_environment.bat tmp.txt nopause

@REM remove temporary file that lists needed packages
DEL tmp.txt 

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: Removed unused packages if no errors above. Press any key to exit
	PAUSE >NUL 
)