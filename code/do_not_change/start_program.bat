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

@REM define local variables like: SET "key=value". Do not have spaces before or after the "=" (unless wanted in value). 
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed:
SET "settings_path=..\non-user_settings.ini"
SET "python_env_activation_code_path=python_environment_code\activate_or_create_environment.bat"
SET "python_code_path=..\main_code.py"
SET "after_python_crash_code_path=..\after_python_crash_code.py"
SET "icon_path=..\icons\icon.ico"

@REM import settings from settings_path:
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( SET %%A=%%B )

@REM move to folder of this file (needed for relative path shortcuts)
@REM current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path=%~dp0"
CD /D "%current_file_path%"

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM change terminal title:
TITLE %program_name%

@REM change terminal colors (for starting lines):

COLOR %terminal_bg_color%%terminal_text_color%

@REM change terminal icon:
change_icon "%program_name%" "%icon_path%"

@REM activate or create & activate python environment:
CALL "%python_env_activation_code_path%" "nopause"

@REM normalize python code paths to full absolute path and get its directory paths:
FOR %%F IN ("%python_code_path%") DO (
    SET "abs_python_code_path=%%~fF"
    SET "python_code_dir=%%~dpF"
)
FOR %%F IN ("%after_python_crash_code_path%") DO (
    SET "abs_crash_python_code_path=%%~fF"
    SET "crash_python_code_dir=%%~dpF"
)

@REM run main python code:
@REM go to directory of python code and execute it and return to folder of this file:
CD /D "%python_code_dir%"
python "%abs_python_code_path%"
CD /D "%current_file_path%"

@REM %ERRORLEVEL% is what the last python execution gives out in sys.exit(errorlevel). 
@REM Errorlevel 1 (default for python crash) will run main_code.py or after_python_crash_code.py (depending on parameter restart_main_code_on_crash in non-user_settings.ini). Errorlevel -1 will exit the terminal. Any other value will pause the terminal until user presses a button (unless this script is called with any argument):
IF %ERRORLEVEL% EQU 1 (
	SET original_python_crashed=1
	CALL :handle_python_crash
)
@REM Does not pause if python returns an errorlevel -1 with sys.exit(-1) in python:
IF %ERRORLEVEL% EQU -1 (
	EXIT /B
)

@REM print final report message:
ECHO:
IF "%original_python_crashed%"=="1" (
	IF "%python_crash_handler_crashed%"=="1" (
		ECHO: ########################################################
		ECHO: Finished all python execution.
		ECHO: The main python code crashed and the python function for
		ECHO: handling crashes crashed at least once before finishing 
		ECHO: successfully now (see above^)
		ECHO: ########################################################
	) ELSE (
		ECHO: ######################################################
		ECHO: Finished all python execution.
		ECHO: The main python code crashed but the python function
		ECHO: for handling crashes finished successfully (see above^)
		ECHO: ######################################################
	)
) ELSE (
	ECHO: #################################
	ECHO: Python code finished successfully
	ECHO: #################################
)
ECHO:

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
@REM define handle_python_crash function:
@REM -------------------------------------------------
:handle_python_crash
ECHO:
ECHO: ###################################################
ECHO: WARNING: Python returned 1, which indicates a crash
ECHO: ###################################################
ECHO:
IF %restart_main_code_on_crash% EQU 0 ( @REM  run after_python_crash_code.py (again)
	IF EXIST "%after_python_crash_code_path%" (
		ECHO:
		ECHO: ###############################################
		ECHO: Running python code intended for after crashes:
		ECHO: ###############################################
		ECHO:
		@REM go to directory of python code and execute it and return to folder of this file:	
		CD /D "%python_code_dir%"
		python "%abs_python_code_path%"
		CD /D "%current_file_path%"
		ECHO:
	@REM exit function if after_python_crash_code does not exist
	) ELSE (
		EXIT /B 0 &@REM exit function with errorcode 0
	)
)	ELSE (  @REM run main_code.py again
	ECHO:
	ECHO: ################################################
	ECHO: Running main python code again after it crashed:
	ECHO: ################################################
	ECHO:
	@REM go to directory of python code and execute it and return to folder of this file:
	CD /D "%crash_python_code_dir%"
	python "%abs_crash_python_code_path%" "crashed" &@REM argument "crashed" indicated to the python code that it is a repeat call after a crash and can be checked for with sys.argv[-1]=="crashed"
	CD /D "%current_file_path%"
	ECHO:
)
IF %ERRORLEVEL% EQU 1 ( @REM could be infinitely recursive
	SET python_crash_handler_crashed=1
	CALL :handle_python_crash
)
EXIT /B 0 &@REM exit function with errorcode 0
@REM -------------------------------------------------
