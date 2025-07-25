@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM define local variables (do not have spaces before or after the "=" and at the end of the line; do not add comments to the lines; use "\" to separate folder levels; do not put "\" at the end of paths):
@REM CAREFUL WITH python_environment_path!
@REM BE VERY CAREFUL WITH THIS PATH: This folder might be deleted if the environment is reset. So do not write something like just ..\..\ which would delete any folder happening to be at that position. Even if you knwo what is at that path, mistakes with relative paths can happen:
SET python_environment_path=..\..\python_environment_code\python_environment
@REM CAREFUL WITH python_environment_path!

@REM delete old environment if existing:
IF EXIST "%~python_environment_path%\Scripts\activate.bat" (
	RD /S /Q "%~python_environment_path%" &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
	IF NOT EXIST "%~python_environment_path%\Scripts\activate.bat" (
		ECHO: Successfully deleted the old python environment
		ECHO:
	) ELSE (
		ECHO:
		ECHO: Error: Failed to deleted the old python environment
		ECHO:
		ECHO: Press any key to exit
		PAUSE >NUL 
		EXIT
	)
)

@REM create new environment:
CALL "create_local_python_environment.bat" %~1 %~2

@REM exit if not called by other script with "nopause" argument:
IF "%~1"=="nopause" ( EXIT /B )
IF "%~2"=="nopause" ( EXIT /B )
ECHO:
ECHO: Press any key to exit
PAUSE >NUL 