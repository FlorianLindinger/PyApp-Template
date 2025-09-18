@REM ########################
@REM --- Code Description ---
@REM ########################

@REM sets OUTPUT=1 if no (or empty) python_version_target given as first argument or if given python version is compatible with the python.exe_path of arg 2. If no path given it will pick the global one. Else it will set OUTPUT=0

@REM #########################
@REM --- Setup & Variables ---
@REM #########################

@REM turn off printing of commands:
@ECHO OFF

@REM make this code local so no variables of a potential calling program are changed:
SETLOCAL

@REM define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
@REM Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET "python_version_target=%~1"
SET "python_exe_path=%~2"

@REM ######################
@REM --- Code Execution ---
@REM ######################

IF "%python_exe_path%"=="" (
	SET "python_exe_path=python"
)

IF "%python_version_target%"=="" (
	ENDLOCAL
	SET "OUTPUT=1"
	EXIT /B
)

@REM split into major.minor.patch
for /f "tokens=1-3 delims=." %%a in ("%python_version_target%") do (
    set "REQ_MAJOR=%%a"
    set "REQ_MINOR=%%b"
    set "REQ_PATCH=%%c"
)

@REM get python version (stdout/stderr safe)
for /f "tokens=2 delims= " %%v in ('%python_exe_path% --version 2^>^&1') do set "python_version_found=%%v"


IF ERRORLEVEL 1 (
	ECHO: Error: Failed to determine python version from "%python_exe_path%" python.exe path. Program aborted: Press any key to exit
	PAUSE>NUL 
	EXIT
)

@REM split into major.minor.patch
for /f "tokens=1-3 delims=." %%a in ("%python_version_found%") do (
    set "CUR_MAJOR=%%a"
    set "CUR_MINOR=%%b"
    set "CUR_PATCH=%%c"
)

@REM compare individually
IF NOT "%CUR_MAJOR%"=="%REQ_MAJOR%" (
	IF NOT "%REQ_MAJOR%"=="" ( GOTO :return_false)
)
IF NOT "%CUR_MINOR%"=="%REQ_MINOR%" (
	IF NOT "%REQ_MINOR%"=="" ( GOTO :return_false)
)
IF NOT "%CUR_PATCH%"=="%REQ_PATCH%" (
	IF NOT "%REQ_PATCH%"=="" ( GOTO :return_false)
)

@REM return true
ENDLOCAL 
SET "OUTPUT=1"

@REM ####################
@REM --- Closing-Code ---
@REM ####################

@REM exit program without closing a potential calling program
EXIT /B

@REM ############################
@REM --- Function Definitions ---
@REM ############################

:return_false
ENDLOCAL 
SET "OUTPUT=0"
EXIT /B

@REM -------------------------------------------------




