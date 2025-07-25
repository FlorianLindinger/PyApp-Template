@REM "@REM" indicates the start of a comment (use "&@REM" for comments after a code line, unless the line starts a nested sequence like a line with IF/ELSE/FOR/..., e.g., "IF A==B ( @REM comment")

@REM turn off printing of commands:
@ECHO OFF

@REM move to folder of this file (needed for relative path shortcuts)
SET current_file_path=%~dp0 &@REM workaround for nieche windows bug where this file gets called with quotation marks
CD /D "%current_file_path%"

@REM make this code local so no variables of a potential calling program are changed:
SETLOCAL

@REM define local variables (do not have spaces before or after the "=" and at the end of the line; do not add comments to the lines; use "\" to separate folder levels; do not put "\" at the end of paths):
SET python_env_code_path=python_environment_code
SET python_code_path=..
SET settings_path=..\non-user_settings.ini
SET icon_path=..\icons\icon.ico

@REM import settings:
FOR /F "tokens=1,2 delims==" %%a IN (%settings_path%) DO (
	IF %%a==program_name (SET program_name=%%b)
	IF %%a==restart_main_code_on_crash (SET restart_main_code_on_crash=%%b)
)

@REM change terminal title:
TITLE %program_name%

@REM change terminal colors (for starting lines):
@REM ; terminal colors (leave empty for windows default. Options: 0=Black,8=Gray,1=Blue,9=LightBlue,2=Green,A=LightGreen,3=Aqua,B=LightAqua,4=Red,C=LightRed,5=Purple,D=LightPurple,6=Yellow,E=LightYellow,7=White,F=BrightWhite):
SET terminal_bg_color=9
SET terminal_text_color=F
COLOR %terminal_bg_color%%terminal_text_color%

@REM change terminal icon:
change_icon "%program_name%" "%icon_path%"

@REM activate or create & activate python environment:
CD /D "%python_env_code_path%" &@REM moving to local folder of called file needed because of relative paths in code
CALL activate_or_create_environment.bat nopause
CD /D "%current_file_path%" &@REM moving back to start directory

@REM go to directory where the python codes are (in order to have them running where they are located):
CD /D "%python_code_path%"

@REM run main python code:
python main_code.py

@REM %ERRORLEVEL% is what the last python execution gives out in sys.exit(errorlevel). 
@REM Errorlevel 1 (default for python crash) will run main_code.py or after_python_crash_code.py (depending on parameter restart_main_code_on_crash in non-user_settings.ini). Errorlevel -1 will exit the terminal. Any other value will pause the terminal until user presses a button (unless this script is called with any argument):
IF %ERRORLEVEL% EQU 1 (
	SET python_crashed=1
	CALL :handle_python_crash
)
@REM Does not pause if python returns an errorlevel -1 with sys.exit(-1) in python:
IF %ERRORLEVEL% EQU -1 (
	EXIT /B
)

@REM print final message:
ECHO:
IF "%python_crashed%"=="1" (
	ECHO: ##########################
	ECHO: Python crashed (see above^)
	ECHO: ##########################
) ELSE (
	ECHO: #################################
	ECHO: Python code finished successfully
	ECHO: #################################
)
ECHO:

@REM pause if not called by other script with "nopause" argument:
IF NOT "%~1"=="nopause" (
	ECHO: Press any key to exit
	PAUSE >NUL 
)

@REM exit program without closing a potential calling program
EXIT /B 

@REM ###################################################################
@REM function definitions:
@REM ###################################################################

@REM define handle_python_crash function:
:handle_python_crash
ECHO:
ECHO: ###################################################
ECHO: WARNING: Python returned 1, which indicates a crash
ECHO: ###################################################
ECHO:
IF %restart_main_code_on_crash% EQU 0 ( @REM  run after_python_crash_code.py (again)
	IF exist after_python_crash_code.py (
		ECHO:
		ECHO: ###############################################
		ECHO: Running python code intended for after crashes:
		ECHO: ###############################################
		ECHO:
		python after_python_crash_code.py
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
	python main_code.py "crashed" &@REM "crashed" indicated to the python code that it is a repeat call after a crash and can be checked for with len(sys.argv)==2
	ECHO:
)
IF %ERRORLEVEL% EQU 1 ( @REM could be infinitely recursive
	CALL :handle_python_crash
)
EXIT /B 0 &@REM exit function with errorcode 0




