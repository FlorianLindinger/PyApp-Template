@echo off
setlocal
cd /d "%~dp0"

:: ===========================
:: local variables

set "VERSION=3.12.10" @REM 3.12.11+ don't have a Windows embeddable zip available
set "INSTALL_DIR=%cd%\..\..\P"
set "ZIP=%INSTALL_DIR%\tmp.zip"
set "URL=https://www.python.org/ftp/python/%VERSION%/python-%VERSION%-embed-amd64.zip"
set "python_exe_name=P.exe"

:: ===========================

:: print
echo Installing backend Python...
echo ============================
echo.

:: Create the installation directory if it doesn't exist.
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Safely clear install dir
for %%I in ("%INSTALL_DIR%") do set "INSTALL_DIR_FULL=%%~fI"
if /i "%INSTALL_DIR_FULL%"=="%cd%\" (
    echo Refusing to delete current directory.
    goto :error_exit
)
if not "%INSTALL_DIR_FULL:~-2%"=="\P" (
    echo Refusing to delete unexpected install dir:
    echo %INSTALL_DIR_FULL%
    goto :error_exit
)
if exist "%INSTALL_DIR_FULL%" (
    rmdir /s /q "%INSTALL_DIR_FULL%"
)
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

:: rename python.exe to P.exe
ren "%INSTALL_DIR%\python.exe" "%python_exe_name%"

:: finish backend installation in python because easier
"%INSTALL_DIR%\P.exe" "%cd%\finish_backend_installation.py"
if errorlevel 1 (
    :: delete the python exe to indicate that installation needs to be retried
    echo Backend Python installation failed during finalization step.
    goto :error_exit
)

:: normal exit
exit /b 0

:: ===========================

:error_exit
:: python_exe missing indicated that not installed -> delete
del "%python_exe%" > nul 2>&1
echo [Error] Backend Python installation failed. Aborting. Press any key to exit.
pause > nul
exit 1
