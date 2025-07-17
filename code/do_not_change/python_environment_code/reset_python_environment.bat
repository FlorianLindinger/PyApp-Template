@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD /D "%~dp0"

@REM define local variables:
@REM CAREFUL WITH python_environment_path!
SET python_environment_path=..\..\python_environment &@REM BE VERY CAREFUL WITH THIS PATH: This folder might be deleted if the environment is reset. So do not write something like just ..\..\ which would delete any folder happening to be at that position. Even if you knwo what is at that path, mistakes with relative paths can happen.
@REM CAREFUL WITH python_environment_path!

@REM delete old environment if existing:
if exist %python_environment_path%\Scripts\activate.bat (
	RD /S /Q %python_environment_path% &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
	if not exist %python_environment_path%\Scripts\activate.bat (
		ECHO: Successfully deleted the old python environment
		ECHO:
	) else (
		ECHO:
		ECHO: Error: Failed to deleted the old python environment
		ECHO:
		ECHO: Press any key to exit
		PAUSE >NUL 
		EXIT
	)
)

@REM create new environment:
call "create_local_python_environment.bat" "nopause"

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: Press any key to exit
	PAUSE >NUL 
	ECHO:
)