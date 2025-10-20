@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PY_VER=3.13"
set "TARGET_DIR=1"
set "PY_ARCH=amd64"


CALL :make_absolute_path_if_relative "%TARGET_DIR%"
SET "TARGET_DIR=%OUTPUT%"

SET "TMP_EXE=tmp.exe"

ECHO: target: %TARGET_DIR%

for /f "usebackq delims=" %%A in (`
  powershell -NoLogo -NoProfile -Command "$v=(Invoke-WebRequest 'https://www.python.org/ftp/python/').Links.href | Where-Object {$_ -match '^%PY_VER%\.\d+/$'} | Sort-Object | Select-Object -Last 1; if($v){$v.TrimEnd('/')}" 
`) do set "FULL_VER=%%A"

if not defined FULL_VER (
    echo ERROR: Could not determine latest patch for %PY_VER%.
    exit /b 1
)

set "PY_EXE=python-%FULL_VER%-%PY_ARCH%.exe"
set "URL=https://www.python.org/ftp/python/%FULL_VER%/%PY_EXE%"

echo URL: %URL%



:: Create target directory if needed
IF not "%TARGET_DIR%"=="" (
    if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" || (
        echo ERROR: Cannot create "%TARGET_DIR%".
        exit /b 1
    )
    
) 


:: Download installer (prefers curl, falls back to PowerShell)
where curl >nul 2>nul
if %ERRORLEVEL%==0 (
  echo Downloading with curl...
  curl -L --fail --retry 5 --retry-delay 2 -o "%TMP_EXE%" "%URL%" || (
    echo ERROR: Download failed via curl.
    exit /b 2
  )
) else (
  echo Downloading with PowerShell...
  powershell -NoLogo -NoProfile -Command ^
    "Try { Invoke-WebRequest -Uri '%URL%' -OutFile '%TMP_EXE%' -UseBasicParsing } Catch { Exit 1 }"
  if not %ERRORLEVEL%==0 (
    echo ERROR: Download failed via PowerShell.
    exit /b 3
  )
)



if not exist "%TMP_EXE%" (
  echo ERROR: Installer not found: %TMP_EXE%
  exit /b 4
)

echo Running silent install...
:: Key choices to avoid interference:
::  - PrependPath=0      -> no PATH changes
::  - Include_launcher=0 -> do not install the Python Launcher (py.exe)
::  - AssociateFiles=0   -> no file associations
::  - Shortcuts=0        -> no Start Menu shortcuts
::  - InstallAllUsers=0  -> per-user install at TargetDir
@REM "%TMP_EXE%" /quiet ^
@REM   InstallAllUsers=0 ^
@REM   TargetDir="%TARGET_DIR%" ^
@REM   PrependPath=0 ^
@REM   Include_pip=1 ^
@REM   Include_launcher=0 ^
@REM   AssociateFiles=0 ^
@REM   Shortcuts=0 ^
@REM   Include_test=0 ^
@REM   Include_doc=0 ^
@REM   CompileAll=1

  start /wait "" "%TMP_EXE%" /quiet ^
  InstallAllUsers=0 ^
  TargetDir="%TARGET_DIR%" ^
  PrependPath=0 ^
  Include_pip=1 ^
  AssociateFiles=0 ^
  Shortcuts=0 ^
  Include_test=0 ^
  CompileAll=1 ^
  /log "%CD%\py-install.log"

:: --- check installer exit code
if errorlevel 1 (
  echo ERROR: Installer returned exit code %ERRORLEVEL%.
  echo Last 40 lines of log:
  powershell -NoLogo -NoProfile -Command "Get-Content -Tail 40 -Path '%CD%\py-install.log'"
  exit /b %ERRORLEVEL%
)

if not exist "%TARGET_DIR%\python.exe" (
  echo ERROR: python.exe not found in "%TARGET_DIR%". Install may have failed.
  exit /b 5
)

echo Verifying...
"%TARGET_DIR%\python.exe" -V || (
  echo ERROR: Python not runnable.
  exit /b 6
)

echo.
echo Done.

exit /b 0



@REM -------------------------------------------------
@REM function that makes relative path (relative to current working directory) to absolute if not already:
@REM -------------------------------------------------
:make_absolute_path_if_relative
	SET "OUTPUT=%~f1"
	GOTO :EOF
@REM -------------------------------------------------