@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
CD "%~dp0"

@REM define local variables
SET non_user_settings_path=..\..\non-user_settings.ini

@REM import settings:
FOR /F "tokens=1,2 delims==" %%a IN (%non_user_settings_path%) DO (
	IF %%a==python_version (SET python_version=%%b)
)

@REM check if any python is installed:
python --version >NUL
if errorlevel 1 (
	ECHO: Error: Install python version %python_version% in windows (https://www.python.org/downloads/windows/^) and restart
	ECHO:
	ECHO: Failed (see above^): Press any key to exit
	PAUSE>NUL 
	EXIT
)

@REM create virtual python environment:
python -m pip install virtualenv
if "%python_version%"=="" (
	python -m virtualenv python_env
) else (
	python -m virtualenv --python=python%python_version% python_env
)

@REM check if environment creation failed:
if not exist "python_env\Scripts\activate.bat" (
	ECHO:
	ECHO:
	ECHO: Failed during installation of python environment (see above^)
	ECHO: Could it be that python version %python_version% is not installed in Windows?
	ECHO: Install (from https://www.python.org/downloads/windows/^) and try again
	ECHO:
	if exist python_env (
		@RD /S /Q python_env &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
		ECHO:
	)
	ECHO: Failed (see above^): Press any key to exit
	PAUSE>NUL 
	EXIT
)

@REM activate environment:
call python_env\Scripts\activate.bat

@REM install packages or create empty requirements.txt file
if exist requirements.txt (
	pip install -r requirements.txt
)  ELSE (
	pip freeze > requirements.txt
)

@REM print environment location:
ECHO:
ECHO Created python%python_version% environment in "%~dp0python_env" if everything worked &@REM %~dp0 gives the local path of the file instead of the caller
ECHO:

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: Press any key to exit
	PAUSE >NUL 
	ECHO:
)