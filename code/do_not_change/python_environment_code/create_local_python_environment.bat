@REM ###################################
@REM --- Code Description & Comments ---
@REM ###################################

@REM "@REM" indicates the start of a comment (use "&@REM" for comments at the end of a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM #########################
@REM --- Setup & Variables ---
@REM #########################

@REM turn off printing of commands:
@ECHO OFF

@REM make this code local so no variables of a potential calling program are changed:
SETLOCAL

@REM move to folder of this file (needed for relative path shortcuts)
@REM current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET current_file_path=%~dp0
CD /D "%current_file_path%"

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value). Add inline comments therefore without a space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths):
SET settings_path=..\..\non-user_settings.ini
SET default_packages_file_path=..\..\python_environment_code\default_python_packages.txt
@REM CAREFUL WITH python_environment_path!
@REM BE VERY CAREFUL WITH THIS PATH: This folder might be deleted if the environment is reset. So do not write something like just ..\..\ which would delete any folder happening to be at that position. Even if you knwo what is at that path, mistakes with relative paths can happen:
SET python_environment_path=..\..\python_environment_code\python_environment
@REM CAREFUL WITH python_environment_path!

@REM import settings from settings_path (e.g., for importing parameter "example" add the line within the last round brackets below "IF %%a==example ( SET example=%%b)"):
FOR /F "tokens=1,2 delims==" %%a IN ('findstr "^" "%settings_path%"') DO (
	IF %%a==python_version ( SET python_version=%%b)
)

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM check if any python is installed:
python --version >NUL
IF errorlevel 1 (
	ECHO: Error: Install python version %python_version% in windows (https://www.python.org/downloads/windows/^) and restart
	ECHO:
	ECHO: Failed (see above^): Press any key to exit
	PAUSE>NUL 
	EXIT
)

@REM upgrade pip
python -m pip install --upgrade pip

@REM create virtual python environment:
python -m pip install --upgrade virtualenv
IF "%python_version%"=="" (
	python -m virtualenv "%python_environment_path%"
) ELSE (
	python -m virtualenv --python=python%python_version% "%python_environment_path%"
)

@REM check if environment creation failed:
IF NOT EXIST "%python_environment_path%\Scripts\activate.bat" (
	ECHO:
	ECHO:
	ECHO: Failed during installation of python environment (see above^)
	ECHO: Could it be that python version %python_version% is not installed in Windows?
	ECHO: Install (from https://www.python.org/downloads/windows/^) and try again
	ECHO:
	IF EXIST "%python_environment_path%" (
		RD /S /Q "%python_environment_path%" &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
		ECHO:
	)
	ECHO: Failed (see above^): Press any key to exit
	PAUSE>NUL 
	EXIT
)

@REM activate environment:
CALL "%python_environment_path%\Scripts\activate.bat"

@REM install packages from file (either default one or one given via argument when calling this batch file or generate empty packages-list-file)
IF NOT "%~1"=="nopause" (
	IF NOT "%~1"=="" (
		IF EXIST %~1 (
			pip install -r %~1
		) ELSE (
			ECHO: Error: %~1 does not exist. Press any key to exit
			PAUSE >NUL 
			EXIT
		)
	) ELSE (
		IF EXIST "%default_packages_file_path%" (
			pip install -r "%default_packages_file_path%"
		) ELSE (
			TYPE NUL > "%default_packages_file_path%"
		)
	)
) ELSE (
	IF EXIST "%default_packages_file_path%" (
		pip install -r "%default_packages_file_path%"
	) ELSE (
		TYPE NUL > "%default_packages_file_path%"
	)
)

@REM print environment location:
CALL :make_absolute_path_if_relative "%current_file_path%%python_environment_path%"
ECHO:
ECHO Created python (version %python_version%) environment in "%OUTPUT%" if everything worked.

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM pause if not called by other script with "nopause" as last argument:
FOR %%a IN (%*) DO SET last_argument=%%~a
IF NOT "%last_argument%"=="nopause" (
	ECHO: Press any key to exit
	PAUSE >NUL 
)

@REM exit program without closing a potential calling program
EXIT /B 

@REM ############################
@REM --- Function Definitions ---
@REM ############################

@REM function that makes path to absolute if not already. Access as %OUTPUT% (also gets rid of unresolved ".." in path):
:make_absolute_path_if_relative
	SET OUTPUT=%~f1
	EXIT /B