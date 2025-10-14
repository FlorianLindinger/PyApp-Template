@echo off
setlocal
:: WIP: add fail print. (also add how to add quotes in quoest. add double ')
:: Usage: make_shortcut.bat "<target>" "<working_dir>" "<icon_path>" "<description>"
:: Example:
:: make_shortcut.bat "C:\Program Files\App\app.exe" "C:\Program Files\App" "C:\icons\app.ico" "My Shortcut"


:: working example:
::create_shortcut.bat "test11" "code\do_not_change\CMD_exes\cmd_1_PyApp-Template.exe" "/C start_program.bat ''..\non-user_settings.ini''" "code\do_not_change" "code\icons\icon.ico" "description"

set "NAME=%~1"
set "TARGET=%~2"
set "ARGS=%~3"
set "WDIR=%~4"
set "ICON=%~5"
set "DESC=%~6"

if "%~1"=="" (
    echo Usage: %~nx0 "name" "target" "args" "working_dir" "icon_path" "description"
    exit /b 1
)

call :make_absolute_path_if_relative "%NAME%"
set "NAME=%output%"
call :make_absolute_path_if_relative "%TARGET%"
set "TARGET=%output%"
call :make_absolute_path_if_relative "%WDIR%"
set "WDIR=%output%"
call :make_absolute_path_if_relative "%ICON%"
set "ICON=%output%"

set "LINK=%NAME%.lnk"

powershell -NoProfile -ExecutionPolicy Bypass ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$lnk = $ws.CreateShortcut('%LINK%');" ^
  "$lnk.TargetPath = '%TARGET%';" ^
  "$lnk.Arguments = '%ARGS%';" ^
  "$lnk.WorkingDirectory = '%WDIR%';" ^
  "$lnk.IconLocation = '%ICON%,0';" ^
  "$lnk.Description = '%DESC%';" ^
  "$lnk.Save()"

echo Shortcut created: %LINK%
exit /b

:make_absolute_path_if_relative
set "output=%~f1"
goto :eof




:: ===============================================
:: function that makes relative path (relative to current working directory) to absolute if not already:
:: Usage: 
::  call :make_absolute_path_if_relative "some_path"
::  set "abs_path=%output%"
:: ===============================================
:make_absolute_path_if_relative
	SET "OUTPUT=%~f1"
	GOTO :EOF
:: ===============================================