:: disable printing of commands
@echo off

:: make variables local
setlocal EnableExtensions DisableDelayedExpansion

:: Work from this file's directory so all relative paths below are stable,
:: regardless of which shortcut, terminal, or current directory started it.
cd /d "%~dp0"

:: ===========================
:: local variables

:: This INI is the single source for the Python version and the two relative paths.
set "SETTINGS_FILE=..\..\settings\backend_settings.ini"

:: ===========================
:: code execution

:: Read only the three supported INI values; spaces around "=" are allowed.
:: Other keys and comments are deliberately ignored by this installer.
for /f "usebackq tokens=1,* delims== " %%A in ("%SETTINGS_FILE%") do (
    if /i "%%A"=="backend_python_version" set "VERSION=%%B"
    if /i "%%A"=="backend_python_install_dir_relative_path" set "INSTALL_DIR_RELATIVE_PATH=%%B"
    if /i "%%A"=="backend_python_finish_installation_relative_path" set "FINISH_INSTALLATION_RELATIVE_PATH=%%B"
)

:: A missing version means the settings file was absent or could not be parsed.
if not defined VERSION goto :refuse_invalid_settings

:: Convert both configured paths to absolute paths relative to the INI file.
:: %%~fI normalizes ".." segments before any destructive operation is possible.
for %%I in ("%SETTINGS_FILE%") do set "SETTINGS_DIR=%%~dpI"
for %%I in ("%SETTINGS_DIR%%INSTALL_DIR_RELATIVE_PATH%") do set "INSTALL_DIR=%%~fI"
for %%I in ("%SETTINGS_DIR%%FINISH_INSTALLATION_RELATIVE_PATH%") do set "FINISH_INSTALLATION_PATH=%%~fI"

:: Build fixed expected locations independently of the configured values.
:: The configuration may describe those paths, but cannot redirect them.
for %%I in ("%SETTINGS_DIR%..\backend_python") do set "EXPECTED_INSTALL_DIR=%%~fI"
for %%I in ("%SETTINGS_DIR%..\scripts\setup\finish_backend_installation.py") do set "EXPECTED_FINISH_INSTALLATION_PATH=%%~fI"
for %%I in ("%~dp0.") do set "SCRIPT_DIR=%%~fI"

:: Refuse the installer directory, every parent directory, and therefore drive roots.
call :is_script_dir_or_parent "%INSTALL_DIR%" "%SCRIPT_DIR%"
if errorlevel 1 goto :refuse_script_dir_or_parent

:: Deletion and finalization are allowed only for these exact resolved locations.
if /i not "%INSTALL_DIR%"=="%EXPECTED_INSTALL_DIR%" goto :refuse_unexpected_dir
if /i not "%FINISH_INSTALLATION_PATH%"=="%EXPECTED_FINISH_INSTALLATION_PATH%" goto :refuse_invalid_settings
if not exist "%FINISH_INSTALLATION_PATH%" goto :refuse_invalid_settings

:: Derived paths are safe because INSTALL_DIR passed every check above.
set "URL=https://www.python.org/ftp/python/%VERSION%/python-%VERSION%-embed-amd64.zip"
set "ZIP=%INSTALL_DIR%\tmp.zip"
set "PYTHON_EXE=%INSTALL_DIR%\python.exe"

:: print
echo Installing backend Python...
echo ============================
echo.

:: This is the only recursive deletion in the installer. It is guarded above.
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
mkdir "%INSTALL_DIR%"

:: Print empty lines because curl may add a banner above its own output.
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

:: Finalization installs backend packages and updates the embedded Python path file.
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

:refuse_script_dir_or_parent
echo Refusing to delete the installer directory or one of its parent directories.
goto :error_exit

:refuse_invalid_settings
echo Refusing missing or invalid backend_settings.ini values.
goto :error_exit

:refuse_unexpected_dir
echo Refusing to delete unexpected install dir:
echo "%INSTALL_DIR%"
goto :error_exit

:error_exit
:: Removing python.exe leaves a clear "not installed" marker for callers that
:: check whether the embedded runtime is ready. This target is derived only after
:: the exact install-path safety check has passed.
del "%PYTHON_EXE%" > nul 2>&1
echo [Error] Backend Python installation failed. Aborting. Press any key to exit.
pause > nul
exit 1

:is_script_dir_or_parent
:: Return errorlevel 1 when the requested delete target is this script directory
:: or any of its ancestors; stop when the traversal reaches the drive root.
set "CHECK_DIR=%~2"
:check_parent
if /i "%~1"=="%CHECK_DIR%" exit /b 1
for %%I in ("%CHECK_DIR%\..") do set "PARENT_DIR=%%~fI"
if /i "%PARENT_DIR%"=="%CHECK_DIR%" exit /b 0
set "CHECK_DIR=%PARENT_DIR%"
goto :check_parent
