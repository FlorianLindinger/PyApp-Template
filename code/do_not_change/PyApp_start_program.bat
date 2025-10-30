:: ========================
:: --- Code Description ---
:: ========================

:: =========================
:: --- Setup & Variables ---
:: =========================

:: turn off printing of commands:
@ECHO OFF

:: make this code local so no variables of a potential calling program are changed:
SETLOCAL

:: get name of current localization language needed for cmd.exe that presumably runs this script
for /f "tokens=2,*" %%A in ('reg query "HKCU\Control Panel\Desktop" /v PreferredUILanguages 2^>nul') do (
	for %%L in (%%B) do (
	set "UI_LANG=%%L"
	goto :done
	)
)
:done
:: create localization language folder if missing
if not exist "CMD_exes\%UI_LANG%\" (
	mkdir "CMD_exes\%UI_LANG%"
	robocopy "CMD_exes\mui_files" "CMD_exes\%UI_LANG%" /E /R:0 /W:0 /NFL /NDL /NJH /NJS /NP
)

:: define local variables
SET "settings_path=%~1"

:: move to folder of this file (needed for relative path shortcuts)
:: current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path=%~dp0"
CD /D "%current_file_path%"

:: check if settings file exist
IF NOT exist "%settings_path%" (
	echo: [Error] Need to define existing settings path. Defined "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)

:: import settings from settings_path:
FOR /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( SET "%%A=%%B" )

:: convert the path settings that are relative to settings file to absolute paths:
FOR %%I IN ("%settings_path%") DO SET "settings_dir=%%~dpI"
CD /D "%settings_dir%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%icon_path%" 
SET "icon_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%python_env_activation_code_path%" 
SET "python_env_activation_code_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%python_code_path%" 
SET "python_code_path=%OUTPUT%"
CALL :MAKE_ABSOLUTE_PATH_IF_RELATIVE "%after_python_crash_code_path%" 
SET "after_python_crash_code_path=%OUTPUT%"
CD /D "%current_file_path%"

:: ======================
:: --- Code Execution ---
:: ======================

:: change terminal title:
TITLE %program_name%

:: change terminal colors (for starting lines):
COLOR %terminal_bg_color%%terminal_text_color%

:: change terminal icon:
change_icon "%program_name%" "%icon_path%"

:: activate or create & activate python environment:
CALL "%python_env_activation_code_path%" "nopause"
IF %ERRORLEVEL% NEQ 0 (
	ECHO: [Error] Environment activation failed (see above). Aborting. Press any key to exit.
	PAUSE >NUL 
	EXIT /B 1
)

:: normalize python code paths to full absolute path and get its directory paths:
FOR %%F IN ("%python_code_path%") DO (
    SET "abs_python_code_path=%%~fF"
    SET "python_code_dir=%%~dpF"
)
FOR %%F IN ("%after_python_crash_code_path%") DO (
    SET "abs_crash_python_code_path=%%~fF"
    SET "crash_python_code_dir=%%~dpF"
)

:: run main python code:
:: go to directory of python code and execute it and return to folder of this file:
CD /D "%python_code_dir%"
python "%abs_python_code_path%"
CD /D "%current_file_path%"

:: %ERRORLEVEL% is what the last python execution gives out in sys.exit(errorlevel). 
:: Errorlevel 1 (default for python crash) will run main_code.py or after_python_crash_code.py (depending on parameter restart_main_code_on_crash in non-user_settings.ini). Errorlevel -1 will exit the terminal. Any other value will pause the terminal until user presses a button (unless this script is called with any argument):
IF %ERRORLEVEL% EQU 1 (
	SET original_python_crashed=1
	CALL :handle_python_crash
)
:: Does not pause if python returns an errorlevel -1 with sys.exit(-1) in python:
IF %ERRORLEVEL% EQU -1 (
	EXIT /B
)

:: print final report message:
ECHO:
IF "%original_python_crashed%"=="1" (
	IF "%python_crash_handler_crashed%"=="1" (
		ECHO: ========================================================
		ECHO: Finished all python execution.
		ECHO: The main python code crashed and the python function for
		ECHO: handling crashes crashed at least once before finishing 
		ECHO: successfully now (see above^)
		ECHO: ========================================================
	) ELSE (
		ECHO: ======================================================
		ECHO: Finished all python execution.
		ECHO: The main python code crashed but the python function
		ECHO: for handling crashes finished successfully (see above^)
		ECHO: ======================================================
	)
) ELSE (
	ECHO: =================================
	ECHO: Python code finished successfully
	ECHO: =================================
)
ECHO:

:: ====================
:: --- Closing-Code ---
:: ====================

:: pause if not called by other script with multiple arguments:
IF "%~2"=="" (
	ECHO: Press any key to exit
	PAUSE >NUL 
)

:: exit program without closing a potential calling program
EXIT /B

:: ====================
:: ==== Functions: ====
:: ====================

:: =================================================
:: function to handle python crashes:
:: =================================================
:handle_python_crash
ECHO:
ECHO: ===================================================
ECHO: WARNING: Python returned 1, which indicates a crash
ECHO: ===================================================
ECHO:
IF %restart_main_code_on_crash% EQU 0 ( @REM  run after_python_crash_code.py (again)
	IF EXIST "%after_python_crash_code_path%" (
		ECHO:
		ECHO: ===============================================
		ECHO: Running python code intended for after crashes:
		ECHO: ===============================================
		ECHO:
		:: go to directory of python code and execute it and return to folder of this file:	
		CD /D "%python_code_dir%"
		python "%abs_python_code_path%"
		CD /D "%current_file_path%"
		ECHO:
	:: exit function if after_python_crash_code does not exist
	) ELSE (
		EXIT /B 0 &@REM exit function with errorcode 0
	)
)	ELSE (  @REM run main_code.py again
	ECHO:
	ECHO: ================================================
	ECHO: Running main python code again after it crashed:
	ECHO: ================================================
	ECHO:
	:: go to directory of python code and execute it and return to folder of this file:
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
:: =================================================



:: =================================================
:: function that makes relative path (relative to current working directory) to :: absolute if not already. Works for empty path (relative) path:
:: Usage:
::    call :make_absolute_path_if_relative "%some_path%"
::    set "abs_path=%output%"
:: =================================================
:make_absolute_path_if_relative
    if "%~1"=="" (
        set "OUTPUT=%CD%"
    ) else (
	    set "OUTPUT=%~f1"
    )
goto :EOF
:: =================================================
