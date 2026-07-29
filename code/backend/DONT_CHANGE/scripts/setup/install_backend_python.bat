:: disable printing of commands
@echo off

:: make variables local
setlocal EnableExtensions DisableDelayedExpansion

:: move to folder of this file
cd /d "%~dp0"

:: ===========================
:: local variables

set "SETTINGS_FILE=..\..\settings\backend_settings.ini"

:: ===========================
:: code execution

:: Read the two supported values. The directory name is validated before use.
for /f "tokens=1,* delims==" %%A in ('findstr /r /i "^backend_python_version[ ]*=" "%SETTINGS_FILE%"') do set "VERSION=%%B"
for /f "tokens=1,* delims==" %%A in ('findstr /r /i "^backend_python_install_dir_name[ ]*=" "%SETTINGS_FILE%"') do set "INSTALL_DIR_NAME=%%B"
for /f "tokens=1,* delims==" %%A in ('findstr /r /i "^backend_python_finish_installation_relative_path[ ]*=" "%SETTINGS_FILE%"') do set "FINISH_INSTALLATION_RELATIVE_PATH=%%B"
if not defined VERSION goto :refuse_invalid_settings
if /i not "%INSTALL_DIR_NAME%"=="backend_python" goto :refuse_invalid_settings
if /i not "%FINISH_INSTALLATION_RELATIVE_PATH%"=="scripts\setup\finish_backend_installation.py" goto :refuse_invalid_settings
for %%I in ("%SETTINGS_FILE%") do set "SETTINGS_DIR=%%~dpI"
set "FINISH_INSTALLATION_PATH=%SETTINGS_DIR%%FINISH_INSTALLATION_RELATIVE_PATH%"
if not exist "%FINISH_INSTALLATION_PATH%" goto :refuse_invalid_settings

:: derived variables
set "INSTALL_DIR=..\..\%INSTALL_DIR_NAME%"
set "URL=https://www.python.org/ftp/python/%VERSION%/python-%VERSION%-embed-amd64.zip"
set "ZIP=%INSTALL_DIR%\tmp.zip"
set "PYTHON_EXE=%INSTALL_DIR%\python.exe"

:: print
echo Installing backend Python...
echo ============================
echo.

:: Safely clear install dir
for %%I in ("%INSTALL_DIR%") do set "INSTALL_DIR_FULL=%%~fI"
for %%I in ("..\..\backend_python") do set "EXPECTED_INSTALL_DIR_FULL=%%~fI"
if /i not "%INSTALL_DIR_FULL%"=="%EXPECTED_INSTALL_DIR_FULL%" goto :refuse_unexpected_dir
if exist "%INSTALL_DIR_FULL%" rmdir /s /q "%INSTALL_DIR_FULL%"
mkdir "%INSTALL_DIR_FULL%"

:: print empty lines because terminal download adds banner ontop
echo.
echo.
echo.
echo.
echo.

:: Download the Python embeddable zip file. The -L flag allows curl to follow redirects, and --fail makes it return an error code if the download fails.
curl -L --fail -o "%ZIP%" "%URL%"
if errorlevel 1 (
    echo Download failed.
    goto :error_exit
)
echo.

:: Unzip the downloaded file to the installation directory. The -Force flag will overwrite existing files without prompting.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%INSTALL_DIR%' -Force"
if errorlevel 1 (
    echo Extraction failed.
    goto :error_exit
)

:: Cleanup temporary installer files
if exist "%ZIP%" del "%ZIP%"

:: finish backend installation in python because easier
"%INSTALL_DIR%\python.exe" "%FINISH_INSTALLATION_PATH%"
if errorlevel 1 (
    :: delete the python exe to indicate that installation needs to be retried
    echo Backend Python installation failed during finalization step.
    goto :error_exit
)

:: normal exit
exit /b 0

:: ===========================
:: functions

:refuse_current_dir
echo Refusing to delete current directory.
goto :error_exit

:refuse_invalid_settings
echo Refusing missing or invalid backend_settings.ini values.
goto :error_exit

:refuse_unexpected_dir
echo Refusing to delete unexpected install dir:
echo "%INSTALL_DIR_FULL%"
goto :error_exit

:error_exit
:: python.exe missing indicates that it is not installed -> delete
del "%PYTHON_EXE%" > nul 2>&1
echo [Error] Backend Python installation failed. Aborting. Press any key to exit.
pause > nul
exit 1
