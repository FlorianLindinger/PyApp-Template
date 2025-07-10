@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM delete old environment if existing:
if exist python_env\Scripts\activate.bat (
	@RD /S /Q python_env &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
	if not exist python_env\Scripts\activate.bat (
		ECHO: Successfully deleted the old python environment
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

@REM pause if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	PAUSE
	ECHO:
)