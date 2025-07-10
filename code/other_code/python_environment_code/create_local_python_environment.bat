@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM import settings in ..\non-user_settings.ini like python_version:
FOR /F "tokens=1,2 delims==" %%a IN ('findstr "^" "..\non-user_settings.ini"') DO (set "%%a=%%b")

@REM check if any python is installed:
python --version 2>NUL
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
	ECHO: Install (https://www.python.org/downloads/windows/^) and restart
	@RD /S /Q python_env &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
	ECHO:
	ECHO: Failed (see above^): Press any key to exit
	PAUSE>NUL 
	EXIT
)

@REM activate environment:
call python_env\Scripts\activate.bat

@REM install packages
if exist requirements.txt (
	pip install -r requirements.txt
) 

@REM print environment location:
ECHO:
ECHO Created python%python_version% environment in "%~dp0python_env"  &:: %~dp0 gives the local path of the file instead of the caller
ECHO:

@REM pause if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	PAUSE
	ECHO:
)