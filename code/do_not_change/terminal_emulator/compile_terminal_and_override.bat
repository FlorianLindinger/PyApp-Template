@echo off
setlocal enableextensions enabledelayedexpansion

pushd "%~dp0" || (
    echo Failed to enter script directory: "%~dp0"
    echo Press any key to exit.
    pause > nul
    exit /b 1
)

REM Build with the shared compile script first. The override script only owns
REM replacing the checked-in compiled folder after a successful build.
set "COMPILE_TERMINAL_NO_PAUSE=yes"
call "compile_terminal.bat"
if errorlevel 1 (
    echo Compile failed. Not replacing "compiled".
    echo Press any key to exit.
    pause > nul
    exit /b 1
)

REM The shared compile script leaves either the pruned dist or the raw dist in
REM DO_NOT_SYNC\build, depending on DO_PRUNE.
set "FINAL_BUILD=DO_NOT_SYNC\build\pruned.dist"
if not exist "!FINAL_BUILD!\" (
    set "FINAL_BUILD=DO_NOT_SYNC\build\run.dist"
)
if not exist "!FINAL_BUILD!\" (
    for /f "delims=" %%D in ('dir "DO_NOT_SYNC\build\*.dist" /b 2^>nul') do (
        set "FINAL_BUILD=DO_NOT_SYNC\build\%%D"
        goto :found_dist
    )
)

:found_dist
if not exist "!FINAL_BUILD!\" (
    echo Final build folder not found in DO_NOT_SYNC\build.
    echo Not replacing "compiled". Press any key to exit.
    pause > nul
    exit /b 1
)

set "COMPILED_DIR=compiled"
set "BACKUP_DIR=DO_NOT_SYNC\compiled_backup"

if exist "!BACKUP_DIR!" (
    echo Removing old backup folder "!BACKUP_DIR!"...
    rmdir /s /q "!BACKUP_DIR!"
    if exist "!BACKUP_DIR!\" (
        echo Failed to remove old backup folder. Not replacing "compiled".
        echo Press any key to exit.
        pause > nul
        exit /b 1
    )
)

if exist "!COMPILED_DIR!" (
    echo Backing up existing "compiled" folder...
    move /y "!COMPILED_DIR!" "!BACKUP_DIR!" > nul
    if errorlevel 1 (
        echo Failed to back up existing "compiled" folder. Not replacing it.
        echo Press any key to exit.
        pause > nul
        exit /b 1
    )
)

echo Replacing "compiled" with "!FINAL_BUILD!"...
move /y "!FINAL_BUILD!" "!COMPILED_DIR!" > nul
if errorlevel 1 (
    echo Failed to move new build into "compiled".
    if exist "!COMPILED_DIR!" rmdir /s /q "!COMPILED_DIR!" > nul 2>&1
    if exist "!BACKUP_DIR!" (
        echo Restoring previous "compiled" folder...
        move /y "!BACKUP_DIR!" "!COMPILED_DIR!" > nul
    )
    echo Press any key to exit.
    pause > nul
    exit /b 1
)

if exist "!BACKUP_DIR!" (
    echo Removing backup of previous "compiled" folder...
    rmdir /s /q "!BACKUP_DIR!"
    if exist "!BACKUP_DIR!\" (
        echo Warning: could not remove backup folder "!BACKUP_DIR!".
    )
)

echo "compiled" successfully replaced.
echo.
echo Press any key to exit.
pause > nul

endlocal
