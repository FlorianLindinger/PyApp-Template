:: WIP: make arg version and make latest default for no arg and test all possibitlies
:: check if it upgrades to 10+ for 9 version
:: check if more final files deletable
:: check if fully portable

@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: find latest python version compatible with PY_VER to find download link
@REM for /f "usebackq delims=" %%A in (`
@REM   powershell -NoLogo -NoProfile -Command "$v=(Invoke-WebRequest 'https://www.python.org/ftp/python/').Links.href | Where-Object {$_ -match '^%PY_VER%\.\d+/$'} | Sort-Object | Select-Object -Last 1; if($v){$v.TrimEnd('/')}" 
@REM `) do set "FULL_VER=%%A"

set "PY_VER=%~1"

for /f "usebackq delims=" %%A in (`
  powershell -NoLogo -NoProfile -Command ^
    "$minor='%PY_VER%';" ^
    "$pattern = ('^' + [regex]::Escape($minor) + '\\.\\d+/$');" ^
    "$all = (Invoke-WebRequest 'https://www.python.org/ftp/python/' -UseBasicParsing).Links |" ^
    "  Where-Object href -match $pattern |" ^
    "  ForEach-Object href | ForEach-Object { $_.TrimEnd('/') } |" ^
    "  Sort-Object {[version]$_} -Descending;" ^
    "foreach($v in $all) {" ^
    "  $url = 'https://www.python.org/ftp/python/' + $v + '/amd64/';" ^
    "  try { (Invoke-WebRequest -Method Head -Uri $url -UseBasicParsing -ErrorAction Stop) > $null; Write-Output $v; exit 0 } catch {}" ^
    "}" ^
    "exit 1"
`) do set "FULL_VER=%%A"


:: abort if fail
ECHO: (%FULL_VER%)
if not defined FULL_VER (
    echo [ERROR] Could not determine latest version for specified in%PY_VER%. Aborting. Press any key to exit.
    PAUSE > NUL
    exit /b 1
)
:: define URL based on full version
set "URL=https://www.python.org/ftp/python/%FULL_VER%/amd64/"
ECHO: Python version: %FULL_VER%
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
CALL :make_absolute_path_if_relative "%TARGET_DIR%"
SET "TARGET_DIR=%OUTPUT%"
rmdir /s /q "%TARGET_DIR%" > NUL
mkdir "%TARGET_DIR%" > NUL

:: install python files
pushd tmp
for /f "delims=" %%M in ('dir /b *.msi') do (
  echo Processing %%M
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

:: delete temporariy folder
rmdir /s /q tmp

:: print success and exit
echo.
echo: Sucessfully created portable Python (%FULL_VER%) at "%TARGET_DIR%". Print any key to exit.
PAUSE > NUL
exit /b 0



:: -------------------------------------------------
:: function that makes relative path (relative to current working directory) to absolute if not already:
:: -------------------------------------------------
:make_absolute_path_if_relative
	SET "OUTPUT=%~f1"
	GOTO :EOF
:: -------------------------------------------------
