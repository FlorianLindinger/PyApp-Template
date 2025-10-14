@REM ########################

@REM Todo:
@REM allow root relaive to this file to delete only stuff in code folder
@REM print what will be delete as abs path and ask. tell size

@REM ########################

@REM =================================================

@REM Safe delete to Recycle Bin ONLY if there is enough capacity.
@REM Usage:
    @REM call safe_recycle_delete.bat "C:\path\to\folder" "optional message"

@REM Exit codes: 0=deleted to bin, 1=user abort, 2+=guards/errors

@REM =================================================

@ECHO OFF

setlocal EnableExtensions EnableDelayedExpansion

SET "RECYCLE_QUOTA_PERCENT=5" &@REM (5 is safe if unknown)
SET "MIN_DEPTH=3"             &@REM (min path depth; 0 = off)
SET "ALLOWED_ROOT=%CD%\..\.." &@REM (optional allow-list root)

set "path=%~1"
set "msg=%~2"
if "%path%"=="" (
  echo: Error: Folder path is required as argument for safe_recycle_delete function. Aborting.
  endlocal & exit /b 2
) ELSE IF NOT EXIST "%path%" (
  ECHO: Error: Folder path does not exist: "%path%". Aborting.
  endlocal & exit /b 3
)
for %%A in ("%path%") do (
  set "abs_path=%%~fA"
  set "DRIVE=%%~dA"
)
if "%msg%"=="" (
  set "msg=Do you want to move the following folder to the recycling bin: ^"!abs_path!^" ?"
)

REM Must exist and be a directory (has at least the directory handle)
if not exist "!abs_path!\*" (
  echo: Error: Not an existing directory: "!abs_path!". Aborting.
  endlocal & exit /b 4
)

REM ----- OPTIONAL allow-list root -----
if defined ALLOWED_ROOT (
  for %%R in ("%ALLOWED_ROOT%") do SET "abs_allowed_root=%%~fR"
)
if defined abs_allowed_root (
  IF /I "!abs_path:%abs_allowed_root%=!"=="!abs_path!" (
    echo: Error: Path not under allowed root: "!abs_path!" ^(root=!abs_allowed_root!^). Aborting.
    endlocal & exit /b 5
  )
)

REM ----- Block drive roots -----
if /I "!abs_path!"=="!DRIVE!" (
  echo: Error: Can't delete drive root: "!abs_path!". Aborting.
  endlocal & exit /b 6
)

REM ----- Block critical locations -----
for %%P in ("%SystemRoot%" "%ProgramFiles%" "%ProgramFiles(x86)%" "%ProgramData%" "%USERPROFILE%") do (
  if /I "%%~fP"=="!abs_path!" (
    echo: Error: Protected path can't be deleted: "!abs_path!". Aborting.
    endlocal & exit /b 7
  )
)
if /I "!abs_path!"=="%CD%"  ( 
  echo: Error: Current working directory is not allowed to be deleted. Aborted.
  endlocal & exit /b 8 
)
if /I "!abs_path!"=="%~dp0" ( 
  echo: Error: Script directory for function "safer_folder_deletion.bat" can't be deleted. Aborting.
  endlocal & exit /b 9 
)

REM ----- Optional minimum depth -----
SET "DEPTH=0"
SET "TMP=%abs_path:\= %"
FOR %%A IN (%TMP%) DO SET /A DEPTH+=1
if %MIN_DEPTH% gtr 0 (
  if !DEPTH! lss %MIN_DEPTH% (
    echo: Error: Path depth !DEPTH! is below minimum %MIN_DEPTH% for folder deletion of "!abs_path!". Aborting. 
    endlocal & exit /b 10
  )
)

@REM REM ----- Require NTFS volume (Recycle Bin reliability) -----
@REM for /f "tokens=* delims=" %%F in ('
@REM   "%powershell_exe%" -NoProfile -Command ^
@REM   "$d='%DRIVE%'.TrimEnd('\'); " ^
@REM   "try { (Get-Volume -DriveLetter $d[0]).FileSystem } catch { (Get-CimInstance Win32_LogicalDisk -Filter ('DeviceID=''{0}''' -f $d)).FileSystem }"
@REM ') do set "FS=%%F"
@REM if /I not "!FS!"=="NTFS" (
@REM   echo: Error: Only NTFS volume folders are allowed to be deleted. Found: !FS!. Aborting.
@REM   endlocal & exit /b 11
@REM )



REM ----- User confirmations -----
echo.
echo !msg!

:ask
ECHO Confirm deletion (Y/N):
SET /P ANSW="":
IF /I "%ANSW%"=="Y" GOTO yes
IF /I "%ANSW%"=="N" GOTO no
ECHO Please enter Y or N:
GOTO ask
:yes
SET "confirmed=1"
GOTO end_ask
:no
SET "confirmed=0"
GOTO end_ask
:end_ask

IF "%confirmed%"=="0" (
  echo: Folder deletion aborted by user.
  endlocal & exit /b 1 
)

SET "powershell_exe=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

REM ===== Capacity checks =====

REM Folder size (bytes)
for /f "tokens=* delims=" %%S in ('
  "%powershell_exe%" -NoProfile -Command ^
  "$p='%abs_path%'; $s=Get-ChildItem -LiteralPath $p -Force -Recurse -ErrorAction SilentlyContinue | Measure-Object -Sum Length; [int64]($s.Sum)"
') do set "DIR_BYTES=%%S"
if not defined DIR_BYTES set "DIR_BYTES=0"

REM Drive total/free (bytes)
for /f "tokens=* delims=" %%T in ('
  "%powershell_exe%" -NoProfile -Command ^
  "$d='%DRIVE%'.TrimEnd('\'); $ld=Get-CimInstance Win32_LogicalDisk -Filter ('DeviceID=''{0}''' -f $d); @([int64]$ld.Size,[int64]$ld.FreeSpace) -join ','"
') do set "DRV=%%T"
for /f "tokens=1,2 delims=," %%a in ("%DRV%") do ( set "DRV_TOTAL=%%a" & set "DRV_FREE=%%b" )

REM Current Recycle Bin usage (bytes) on this drive
for /f "tokens=* delims=" %%U in ('
  "%powershell_exe%" -NoProfile -Command ^
  "$d='%DRIVE%'.TrimEnd('\'); $rb=Join-Path $d '\$Recycle.Bin'; " ^
  "if (Test-Path $rb) { (Get-ChildItem -LiteralPath $rb -Force -Recurse -ErrorAction SilentlyContinue | Measure-Object -Sum Length).Sum } else { [int64]0 }"
') do set "BIN_USED=%%U"
if not defined BIN_USED set "BIN_USED=0"

REM Estimated quota (bytes)
for /f "tokens=* delims=" %%Q in ('
  "%powershell_exe%" -NoProfile -Command ^
  "[int64]([double]('%RECYCLE_QUOTA_PERCENT%')/100.0 * [double]('%DRV_TOTAL%'))"
') do set "BIN_QUOTA=%%Q"

REM Estimated free space in bin
for /f "tokens=* delims=" %%F in ('
  "%powershell_exe%" -NoProfile -Command "[int64]('%BIN_QUOTA%') - [int64]('%BIN_USED%')"
') do set "BIN_FREE_EST=%%F"

echo.
echo [INFO] Folder size:          !DIR_BYTES! bytes
echo [INFO] Recycle Bin used:     !BIN_USED! bytes
echo [INFO] Recycle Bin quota:    !BIN_QUOTA! bytes  (%RECYCLE_QUOTA_PERCENT%%% of drive)
echo [INFO] Recycle Bin free est.:!BIN_FREE_EST! bytes
echo [INFO] Drive free space:     !DRV_FREE! bytes

for /f "tokens=* delims=" %%C in ('
  "%powershell_exe%" -NoProfile -Command ^
  "([int64]('%DIR_BYTES%') -le [int64]('%BIN_FREE_EST%')) -and ([int64]('%DIR_BYTES%') -le [int64]('%DRV_FREE%'))"
') do set "CAN_RECYCLE=%%C"

if /I not "!CAN_RECYCLE!"=="True" (
  echo.
  echo: Error: Not enough recycle bin capacity (or disk free) to safely delete folder at "!abs_path!". Aborting.
  echo: -> Delete manually or empty/increase the recycle bin.
  endlocal & exit /b 12
)

REM ===== Send to Recycle Bin (Explorer-equivalent) =====
for /f "tokens=* delims=" %%E in ('
  "%powershell_exe%" -NoProfile -Command ^
  "Add-Type -AssemblyName Microsoft.VisualBasic; " ^
  "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory(" ^
  "  '%abs_path%'," ^
  "  [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs," ^
  "  [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin" ^
  ")"
') do set "PSOUT=%%E"

REM Verify (do NOT permanently delete on failure)
if exist "!abs_path!\*" (
  echo: Error: Windows refused the Recycle Bin move (or it failed^). Nothing was permanently deleted. Aborting.
  echo: -> Delete manually.
  endlocal & exit /b 13
)

endlocal & exit /b 0


