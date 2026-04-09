:: ========================
:: --- Code Description ---
:: ========================

:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands and make definitions local
@ECHO OFF & SETLOCAL

:: handle args
set "output_file_path=%~1"

:: set default if not given
if "%output_file_path%"=="" (
	set "output_file_path=requirements.txt"
)

:: make path absolute if not
call :set_abs_path "%output_file_path%" "output_file_path"

:: ======================
:: --- Code Execution ---
:: ======================

:: print warning if file already exists:
IF EXIST "%output_file_path%" (
   ECHO [Warning] "%output_file_path%" already exists and will be overwritten.
	ECHO:
)

:: generate file:
(for /f "delims==" %%a in ("pip list --format=freeze") do @echo %%a) > "%output_file_path%"

:: print success/fail and exit
if exist "%output_file_path%" (
	echo: [Success] Generated "%output_file_path%"
	ECHO:
	exit /b 0
) else (
	echo: [Error] Failed to generate "%output_file_path%". See above. Press any key to exit.
	pause > nul
	ECHO:
	exit /b 1
)

:: ====================
:: ==== Functions: ====
:: ====================

::::::::::::::::::::::::::::::::::::::::::::::::
:: function that converts relative (to current working directory) path {arg1} to absolute and sets it to variable {arg2}. Works for empty path {arg1} which then sets the current working directory to variable {arg2}. Raises error if {arg2} is missing:
:: Usage:
::    call :set_abs_path "%some_path%" "some_path"
::::::::::::::::::::::::::::::::::::::::::::::::
:set_abs_path
    if "%~2"=="" (
        echo [Error] Second argument is missing for :set_abs_path function in "%~f0". (First argument was "%~1"^). 
        echo Aborting. Press any key to exit.
        pause > nul
        exit /b 1
    )
    if "%~1"=="" (
        set "%~2=%CD%"
    ) else (
	    set "%~2=%~f1"
    )
goto :EOF
:: =================================================