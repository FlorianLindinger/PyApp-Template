@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM define local variables
SET python_env_code_path=python_environment_code
SET python_code_path=..\
SET settings_path=..\non-user_settings.ini

@REM import settings:
FOR /F "tokens=1,2 delims==" %%a IN (%settings_path%) DO (
	IF %%a==terminal_name (SET terminal_name=%%b)
	IF %%a==restart_main_code_on_crash (SET restart_main_code_on_crash=%%b)
	IF %%a==terminal_bg_color (SET terminal_bg_color=%%b)
	IF %%a==terminal_text_color (SET terminal_text_color=%%b)
)

@REM change terminal title:
TITLE %terminal_name%

@REM change terminal colors
COLOR %terminal_bg_color%%terminal_text_color%

@REM activate or create & activate python environment:
CD %python_env_code_path% &@REM moving to local folder of called file needed because of relative paths in code
call activate_or_create_environment.bat "nopause"
CD "%~dp0" &@REM moving back to start directory

@REM go to directory where the python codes are (in order to have them running where they are located):
CD %python_code_path%

@REM run main python code:
python main_code.py
ECHO:

@REM %ERRORLEVEL% is what the last python execution gives out in sys.exit(errorlevel). 
@REM Errorlevel 1 (default for python crash) will run main_code.py or after_python_crash_code.py (depending on parameter restart_main_code_on_crash in non-user_settings.ini). Errorlevel -1 will exit the terminal. Any other value will pause the terminal until user presses a button (unless this script is called with any argument):
IF %ERRORLEVEL% EQU 1 (
	CALL :handle_python_crash
)
@REM Does not pause if python returns an errorlevel -1 with sys.exit(-1) in python:
IF %ERRORLEVEL% EQU -1 (
	EXIT
)

@REM exit if not called by other script with any argument:
IF "%~1"=="" (
	ECHO:
	ECHO: python code finished successfully. Press any key to exit
	PAUSE >NUL 
	ECHO:
)

@REM exit before function definition would be called irroniously:
EXIT 

@REM ###################################################################
@REM function definitions:
@REM ###################################################################

@REM define handle_python_crash function:
:handle_python_crash
ECHO:
ECHO: Warning: Python returned 1, which indicates a crash
ECHO:
IF %restart_main_code_on_crash% EQU 0 ( @REM  run after_python_crash_code.py (again)
	PAUSE
	IF exist after_python_crash_code.py ( 	
		ECHO:
		ECHO: Running python code intended for after crashes:
		ECHO:
		@ECHO ON
		python after_python_crash_code.py
		@ECHO OFF
		ECHO:
	@REM exit function if after_python_crash_code does not exist
	) ELSE (
		EXIT /B 0 &@REM exit function with errorcode 0
	)
)	ELSE (  @REM run main_code.py again
	ECHO:
	ECHO: Running main python code again after it crashed:
	ECHO:
	@ECHO ON
	python main_code.py "crashed"
	@ECHO OFF
	ECHO:
)
IF %ERRORLEVEL% EQU 1 ( @REM could be infinitely recursive
	CALL :handle_python_crash
)
EXIT /B 0 &@REM exit function with errorcode 0




