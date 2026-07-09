:: disable printing of commands
@echo off

:: make variables local
setlocal EnableExtensions DisableDelayedExpansion

:: move to folder of this file
cd /d "%~dp0"

:: ===========================
:: local variables

:: version must have embeddible zip available:
set "VERSION=3.12.10"
set "SETUP_DIR=%~dp0"
set "INSTALL_DIR=%SETUP_DIR%..\..\backend_python"
set "PYTHON_EXE=%INSTALL_DIR%\python.exe"
set "ZIP=%INSTALL_DIR%\tmp.zip"
set "URL=https://www.python.org/ftp/python/%VERSION%/python-%VERSION%-embed-amd64.zip"

:: ===========================
:: code execution

:: print
echo Installing backend Python...
echo ============================
echo.

:: Create the installation directory if it doesn't exist.
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Safely clear install dir
for %%I in ("%INSTALL_DIR%") do set "INSTALL_DIR_FULL=%%~fI"
for %%I in ("%SETUP_DIR%.") do set "SETUP_DIR_FULL=%%~fI\"
if /i "%INSTALL_DIR_FULL%"=="%SETUP_DIR_FULL%" goto :refuse_current_dir
if /i not "%INSTALL_DIR_FULL:~-15%"=="\backend_python" goto :refuse_unexpected_dir
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
"%INSTALL_DIR%\python.exe" "%SETUP_DIR%finish_backend_installation.py"
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
