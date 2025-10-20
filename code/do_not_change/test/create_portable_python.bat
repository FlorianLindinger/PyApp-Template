@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PY_VER=3.13"

:: find latest python version compatible with PY_VER to find download link
for /f "usebackq delims=" %%A in (`
  powershell -NoLogo -NoProfile -Command "$v=(Invoke-WebRequest 'https://www.python.org/ftp/python/').Links.href | Where-Object {$_ -match '^%PY_VER%\.\d+/$'} | Sort-Object | Select-Object -Last 1; if($v){$v.TrimEnd('/')}" 
`) do set "FULL_VER=%%A"
if not defined FULL_VER (
    echo [ERROR] Could not determine latest patch for %PY_VER%.
    exit /b 1
)
set "URL=https://www.python.org/ftp/python/%FULL_VER%/amd64/"
ECHO: Download URL: %URL%

:: (re)create tmp file
rmdir /s /q tmp > NUL
mkdir tmp

:: downlaod files
powershell -NoLogo -NoProfile -Command ^
  "$base='%URL%';" ^
  "$out='tmp';" ^
  "$links=(Invoke-WebRequest -Uri $base).Links | Where-Object href -ne $null | ForEach-Object { $_.href } |" ^
  " Where-Object {$_ -notmatch '/$'} |" ^
  " ForEach-Object { if($_ -match '^https?://') {$_} else {$base + $_} } |" ^
  " Where-Object { -not ( ([IO.Path]::GetFileNameWithoutExtension( ([IO.Path]::GetFileNameWithoutExtension($_)) )) -match '(_d|_pdb)$' ) };" ^
  "foreach($l in $links){$n=[IO.Path]::GetFileName($l);$p=Join-Path $out $n;Try{Invoke-WebRequest -Uri $l -OutFile $p -UseBasicParsing}catch{Write-Error $l}}"

:: (re)create final installation folder
set "TARGET_DIR=portable_python"
rmdir /s /q "%TARGET_DIR%" > NUL
mkdir "%TARGET_DIR%" > NUL

:: install python files
pushd tmp
for /f "delims=" %%M in ('dir /b *.msi') do (
  msiexec /a "%%~fM" TARGETDIR="%TARGET_DIR%" INSTALLDIR="%TARGET_DIR%" /qn
)
popd

:: create a "python.exe" that only sees local paths 
SET "local_python_name=local_only_python.bat"
> "%TARGET_DIR%\%local_python_name%" (
  echo @echo off
  echo setlocal
  echo set "ROOT=%%~dp0"
  echo set "PATH=%%ROOT%%;%%ROOT%%\Scripts;%%SystemRoot%%\System32;%%SystemRoot%%"
  echo call "%%ROOT%%python.exe" %%*
  echo endlocal ^& exit /b %%ERRORLEVEL%%
)

:: verify functioning %local_python_name%
CALL "%TARGET_DIR%\%local_python_name%" -V || (
  echo [ERROR] Local Python not runnable. Aborting. Press any key to exit.
  PAUSE > NUL
  EXIT /B 2
)

:: print
echo.
echo Done.

:: delete temporariy folder
rmdir /s /q tmp

:: success exit at end of code
exit /b 0

@REM -------------------------------------------------
@REM function that makes relative path (relative to current working directory) to absolute if not already:
@REM -------------------------------------------------
:make_absolute_path_if_relative
	SET "OUTPUT=%~f1"
	GOTO :EOF
@REM -------------------------------------------------
