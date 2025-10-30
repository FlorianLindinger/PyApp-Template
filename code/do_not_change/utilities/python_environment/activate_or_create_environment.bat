:: ========================
:: --- Code Description ---
:: ========================



:: =========================
:: --- Setup & Variables ---
:: =========================

:: turn off printing of commands:
@ECHO OFF

:: this code can't use SETLOCAL to not overwrite global variables because the python environment activation won't work then. Therefore the local variables use unlikely labels:
:: In order to not move the current directory of the calling script, this script manually moves back to the starting path
SET "starting_path_aoce=%CD%"

:: check if necessary arguments are given
IF "%~1"=="" (
	ECHO: [Error] Missing argument: Define settings path as argument for script "%~f0". Aborting. Press any key to exit.
	PAUSE > NUL
	EXIT /B 1
)

:: define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
:: Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET "settings_path_aoce=%~1"
SET "python_environment_path_aoce=..\..\..\python_environment_code\python_environment"
SET "python_extra_packages_folder_aoce=..\..\..\python_environment_code\installed_python_packages"

:: make path absolute
CALL :make_absolute_path_if_relative "%python_environment_path_aoce%"
SET "python_environment_path_aoce=%OUTPUT%"

:: import the python_version setting from into python_version_aoce variable:
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path_aoce%"') DO (
	IF "%%A"=="python_version" (
		SET "python_version_aoce=%%B"
		GOTO :stop
	)
)
:: fail case:
CALL :make_absolute_path_if_relative "%settings_path_aoce%"
SET "settings_path_aoce=%OUTPUT%"
ECHO: [Error] Setting "python_version" not found in "%settings_path_aoce%". Aborting. Press any key to exit.
PAUSE > NUL
EXIT /B 2
:: sucess case:
:stop

:: move to folder of this file (needed for relative path shortcuts)
:: current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path_aoce=%~dp0"
CD /D "%current_file_path_aoce%"

:: ======================
:: --- Code Execution ---
:: ======================

:: create environment if not existing and activate it:
IF NOT EXIST "%python_environment_path_aoce%" (
	ECHO:
	ECHO: Creating local python environment and packages folder for first execution
	ECHO:
	CALL create_local_python_environment.bat "nopause"
	CALL "%python_environment_path_aoce%\Scripts\activate.bat"
	CALL setup_external_folder_for_additional_python_packages.bat
	CALL install_packages_from_list.bat ""
) ELSE (
	CALL check_if_python_version_matches.bat "%python_version_aoce%" "%python_environment_path_aoce%\Scripts\python.exe"
	IF %OUTPUT%==0 (
		ECHO:
		ECHO: Delete python environment with wrong version at folder path: "%python_environment_path_aoce%"? (recommended after confirmation of folder path^). 
		CHOICE /c YN /m Enter y/n for Yes/No
		IF %ERRORLEVEL%==1 (
			RD /S /Q "%python_environment_path_aoce%" &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
		)
		IF EXIST "%extra_folder_exist%" (
			ECHO:
			ECHO: Delete python extra packages folder for reinstalling packages for different python version "%extra_folder_exist%"? (recommended after confirmation of folder^). 
			CHOICE /c YN /m Enter "y"/"n" for Yes/No
			IF %ERRORLEVEL%==1 (
				RD /S /Q "%extra_folder_exist%" &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
			)
		)
		ECHO:
		ECHO: Recreating local python environment and packages folder
		ECHO:
		CALL create_local_python_environment.bat "nopause"
		CALL "%python_environment_path_aoce%\Scripts\activate.bat"
		CALL setup_external_folder_for_additional_python_packages.bat
		CALL install_packages_from_list.bat ""
	) ELSE (
		CALL "%python_environment_path_aoce%\Scripts\activate.bat"
	)
)

@REM IF %ERRORLEVEL% NEQ 0 (
@REM 	ECHO: [Error] Failed activation of environment via "%python_environment_path_aoce%\Scripts\activate.bat". Aborting. Press any key to exit.
@REM 	PAUSE >NUL 
@REM 	EXIT /B 2
@REM )

:: ====================
:: --- Closing-Code ---
:: ====================

:: pause if not called by other script with any argument:
IF "%~1"=="" (
	ECHO: Press any key to exit
	PAUSE >NUL 
)

:: move back to starting path:
CD /D %starting_path_aoce%

:: exit program without closing a potential calling program
EXIT /B 

:: ============================
:: --- Function Definitions ---
:: ============================

:: -------------------------------------------------
:: function that makes relative path (relative to current working directory) to absolute if not already:
:: -------------------------------------------------
:make_absolute_path_if_relative
	SET "OUTPUT=%~f1"
	GOTO :EOF
:: -------------------------------------------------

:: -------------------------------------------------
:: function that prompt user to confirm if folder at path can be deleted and deletes if and stops program else with a message to the user. First agrument is the path which is to be deleted and the second one is a custom message to the user. If none given it prints ""
:: -------------------------------------------------
:delete_folder_after_confirmation
	SETLOCAL
	
	SET "folder_path=%~1"
	IF NOT "%~2"=="" (
		SET "message=%~2"
	) ELSE (
		SET "message=Delete folder at folder path: ""%folder_path%""? (recommended after confirmation of correct folder path^):"
	)

	IF "%folder_path%"=="" (
		ECHO: ERROR: Folder path can't be empty for folder that is ment to be deleted!
		ENDLOCAL
		GOTO :EOF
	) 
	
	ECHO: %message%
	CHOICE /c YN /m Delete? Enter y/n for Yes/No
	IF %ERRORLEVEL%==1 (
		ECHO "%folder_path%"
		@REM RD /S /Q "%folder_path%" &@REM CAREFULL. DELETES EVERYTHING IN THAT FOLDER
	)

	ENDLOCAL
	GOTO :EOF
:: -------------------------------------------------
