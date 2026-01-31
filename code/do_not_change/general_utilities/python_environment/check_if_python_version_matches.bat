:: ========================
:: --- Code Description ---
:: ========================

:: Sets globally OUTPUT=1 if no (or empty) python_version_target given as first argument or if given python version is compatible with the python.exe_path of arg 2. If no path given it will pick the global one. Else it will set globally OUTPUT=0. If the first arg is empty it will set OUTPUT=1 because it assumes every version is matching.

:: =========================
:: --- Setup & Variables ---
:: =========================

:: turn off printing of commands & :: make this code local so no variables of a potential calling program are changed
@echo off & setlocal

:: define local variables (do not have spaces before or after the "=" or at the end of the variable value (unless wanted in value) -> inline comments without space before "&@REM".
:: Use "\" to separate folder levels and omit "\" at the end of paths. Relative paths allowed):
SET "python_version_target=%~1"
SET "python_exe_path=%~2"

:: ======================
:: --- Code Execution ---
:: ======================

IF "%python_exe_path%"=="" (
	SET "python_exe_path=python"
)

IF "%python_version_target%"=="" (
	ENDLOCAL
	SET "OUTPUT=1"
	EXIT /B 0
)

:: split into major.minor.patch
for /f "tokens=1-3 delims=." %%a in ("%python_version_target%") do (
    set "REQ_MAJOR=%%a"
    set "REQ_MINOR=%%b"
    set "REQ_PATCH=%%c"
)

:: normalize: remove any quotes that may already be present
set "python_exe_path=%python_exe_path:"=%"

echo "%python_exe_path%"


set "python_exe_path=%python_exe_path:"=%"
echo python_exe_path="%python_exe_path%"
echo 1
if exist "%python_exe_path%" (
  echo 1.1
) else (
  echo 1.2
)
if not exist "%python_exe_path%" (
  echo 1.3
) else (
  echo 1.4
)


if not exist "%python_exe_path%" (
  echo [Error] python.exe does not exist: "%python_exe_path%"
  echo 2
  pause >nul
  exit /b 1
)

echo 3

:: get python version (stdout/stderr safe)
set "python_version_found="
set "tmp_out=%TEMP%\pyver_%RANDOM%.txt"

"%python_exe_path%" -c "import sys; print(sys.version.split()[0])" > "%tmp_out%" 2>&1
set "rc=%ERRORLEVEL%"

echo 4

set /p "python_version_found="<"%tmp_out%"
del "%tmp_out%" >nul 2>&1

if not "%rc%"=="0" (
  echo [Error] Python failed to run: "%python_exe_path%"
  echo Output: "%python_version_found%"
  pause >nul
  exit /b 1
)

echo 5

:: split into major.minor.patch
for /f "tokens=1-3 delims=." %%a in ("%python_version_found%") do (
    set "CUR_MAJOR=%%a"
    set "CUR_MINOR=%%b"
    set "CUR_PATCH=%%c"
)

:: compare individually
IF NOT "%CUR_MAJOR%"=="%REQ_MAJOR%" (
	IF NOT "%REQ_MAJOR%"=="" ( GOTO :return_false)
)
IF NOT "%CUR_MINOR%"=="%REQ_MINOR%" (
	IF NOT "%REQ_MINOR%"=="" ( GOTO :return_false)
)
IF NOT "%CUR_PATCH%"=="%REQ_PATCH%" (
	IF NOT "%REQ_PATCH%"=="" ( GOTO :return_false)
)

echo 6

:: return true
ENDLOCAL 
SET "OUTPUT=1"

:: ====================
:: --- Closing-Code ---
:: ====================

:: exit program without closing a potential calling program
EXIT /B 0

:: ============================
:: --- Function Definitions ---
:: ============================

:return_false
ENDLOCAL 
SET "OUTPUT=0"
EXIT /B 0

:: -------------------------------------------------




