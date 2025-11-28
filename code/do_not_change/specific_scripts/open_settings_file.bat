:: ========================
:: --- Code Description ---
:: ========================

:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands & make variables local
@echo off & setlocal

:: define local variables (with relative paths being relative to this file)
set "settings_path=..\..\non-user_settings.ini"

:: get current file path
set "current_file_path=%~dp0"
:: move to folder of this file (needed for relative path)
cd /d "%current_file_path%"

:: check if file exist
if not exist "%settings_path%" (
	echo [Error] "%settings_path%" does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)

:: import settings from settings_path: user_settings_path
for /F "tokens=1,2 delims==" %%A IN ('findstr "^" "%settings_path%"') DO ( set "%%A=%%B" )

if "%user_settings_path%"=="" (
	echo [Error] "user_settings_path" not defined in "%settings_path%". Aborting. Press any key to exit.
	pause > nul
	exit /b 2
)

:: go to folder of settings_path
for %%I IN ("%settings_path%") DO set "settings_dir=%%~dpI"
cd /d "%settings_dir%"

:: open settings file
start "" "%user_settings_path%"

:: exit if no error
if errorlevel 0 (
	exit 0
)

:: print error
echo [Error] Failed to open settings file. Press any key to exit.
pause > nul
exit 3



