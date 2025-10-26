@REM ########################
@REM --- Code Description ---
@REM ########################

@REM #########################
@REM --- Setup & Variables ---
@REM #########################

@REM turn off printing of commands:
@ECHO OFF

@REM make this code local so no variables of a potential calling program are changed:
SETLOCAL

@REM move to folder of this file (needed for relative path shortcuts)
@REM current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path=%~dp0"
CD /D "%current_file_path%"

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET "settings_path=..\..\non-user_settings.ini"
@REM CAREFUL WITH python_environment_path!
@REM BE VERY CAREFUL WITH THIS PATH: This folder might be deleted if the environment is reset. So do not write something like just ..\..\ which would delete any folder happening to be at that position. Even if you knwo what is at that path, mistakes with relative paths can happen:
SET "python_environment_path=..\..\python_environment_code\python_environment"
@REM CAREFUL WITH python_environment_path!

@REM import settings from settings_path (e.g., for importing parameter "example" add the line within the last round brackets below "IF %%A==example ( SET example=%%B)"):
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO (
	IF %%A==python_version ( SET "python_version=%%B")
)

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM check if any python is installed and warn & abort if missing:
IF "%python_version%"=="" (
	python --version >NUL
	IF ERRORLEVEL 1 (
		ECHO: Error: Missing a python installation: Install python in Windows (https://www.python.org/downloads/windows/^). Program aborted: Press any key to exit
		PAUSE>NUL 
		EXIT
	)
) ELSE (
	python%python_version% --version >NUL
	IF ERRORLEVEL 1 (
		ECHO: Error: Missing specific python installation: Install python version %python_version% in Windows (https://www.python.org/downloads/windows/^). Program aborted: Press any key to exit
		PAUSE>NUL 
		EXIT
	)
)

@REM install virtualenv package if missing:
python -c "import virtualenv" 2>NUL
IF NOT %ERRORLEVEL%==0 (
	python -m pip install virtualenv --disable-pip-version-check
)

@REM create virtual python environment:
IF "%python_version%"=="" (
	python -m virtualenv "%python_environment_path%"
) ELSE (
	python -m virtualenv --python=python%python_version% "%python_environment_path%"
)

@REM check if environment creation failed:
IF NOT EXIST "%python_environment_path%\Scripts\activate.bat" (
	ECHO:
	ECHO:
	IF EXIST "%python_environment_path%" (
		ECHO: Delete faulty folder "%python_environment_path%"? (recommended after confirmation of folder^). 
		CHOICE /c YN /m Enter "y"/"n" for Yes/No^
		IF %ERRORLEVEL%==1 (
			RD /S /Q "%python_environment_path%" &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
		)
		EXIT
	) ELSE (
		ECHO: Error: Failed during installation of python environment (see above^)
		ECHO:
		ECHO: Press any key to exit
		PAUSE>NUL 
		EXIT
	)
)

@REM print environment location:
CALL :make_absolute_path_if_relative "%current_file_path%%python_environment_path%"
ECHO:
ECHO Created python (version %python_version%) environment in "%OUTPUT%" if everything worked.

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM pause if not called by other script with any argument:
IF "%~1"=="" (
	ECHO: Press any key to exit
	PAUSE >NUL 
)

@REM exit program without closing a potential calling program
EXIT /B 

@REM ############################
@REM --- Function Definitions ---
@REM ############################

@REM -------------------------------------------------
@REM function that makes relative path (relative to current working directory) to absolute if not already:
@REM -------------------------------------------------
:make_absolute_path_if_relative
	SET "OUTPUT=%~f1"
	GOTO :EOF
@REM -------------------------------------------------