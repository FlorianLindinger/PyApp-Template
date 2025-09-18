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

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET "base_venv_path=..\..\python_environment_code\python_environment"
SET "installed_packages_path=..\..\python_environment_code\installed_python_packages"

@REM move to folder of this file (needed for relative path shortcuts)
@REM current_file_path varaible needed as workaround for nieche windows bug where this file gets called with quotation marks:
SET "current_file_path=%~dp0"
CD /D "%current_file_path%"

@REM convert the path settings that are relative to settings file to absolute paths:
@REM make paths to absolute if relative paths:
CALL :make_absolute_path_if_relative %base_venv_path%
SET "base_venv_path=%OUTPUT%"
CALL :make_absolute_path_if_relative %installed_packages_path%
SET "installed_packages_path=%OUTPUT%"

@REM ######################
@REM --- Code Execution ---
@REM ######################

@REM delete gitignore in order to sync base python in git:
DEL "%base_venv_path%\.gitignore"

@REM create external packages folder if not existing:
IF NOT EXIST "%installed_packages_path%" (
    MKDIR "%installed_packages_path%"
)

@REM add .pth into base_venv_path site-packages to link to new folder:
SET "PTHFILE=%base_venv_path%\Lib\site-packages\external.pth"
ECHO %installed_packages_path%>"%PTHFILE%"

@REM add line to activate.bat to set the location of pip installs if not already there:
SET "activate_path=%base_venv_path%\Scripts\activate.bat"
FINDSTR /c:"PIP_TARGET" "%activate_path%" >NUL
IF ERRORLEVEL 1 (
    ECHO.>>"%activate_path%"
    ECHO @REM === auto-added for installing with pip to custom path ===>>"%activate_path%"
    ECHO @SET "PIP_TARGET=%installed_packages_path%">>"%activate_path%"
) 

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

