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
	output_file_path="requirements.txt"
)

:: make path absolute if not
call :make_absolute_path_if_relative "%output_file_path%"
set "output_file_path=%OUTPUT%"

:: ======================
:: --- Code Execution ---
:: ======================

:: print warning if file already exists:
IF EXIST "%output_file_path%" (
   ECHO [Warning] "%output_file_path%" already exists and will be overwritten.
	ECHO:
)

:: generate file:
python -m pip freeze --disable-pip-version-check > "%output_file_path%"

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
:: function that makes relative path (relative to current working directory) to :: absolute if not already. Works for empty path (relative) path:
:: Usage:
::    call :make_absolute_path_if_relative "%some_path%"
::    set "abs_path=%output%"
::::::::::::::::::::::::::::::::::::::::::::::::
:make_absolute_path_if_relative
    if "%~1"=="" (
        set "OUTPUT=%CD%"
    ) else (
	    set "OUTPUT=%~f1"
    )
goto :EOF
:: =================================================
:: =================================================