:: Install an embeddable CPython distribution.
::
:: Usage:
::   call install_embedded_python.bat <version> <install-dir>
::
:: Parameters:
::   %1  CPython version, for example 3.14.0
::   %2  Absolute or relative destination directory

@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "VERSION=%~1"
set "INSTALL_DIR_INPUT=%~2"
if not defined VERSION goto :usage
if not defined INSTALL_DIR_INPUT goto :usage

for %%I in ("%INSTALL_DIR_INPUT%") do set "INSTALL_DIR=%%~fI"
for %%I in ("%~dp0.") do set "SCRIPT_DIR=%%~fI"

:: Never let this generic helper delete itself, an ancestor, or a drive root.
call :is_script_dir_or_parent "%INSTALL_DIR%" "%SCRIPT_DIR%"
if errorlevel 1 goto :refuse_script_dir_or_parent

set "URL=https://www.python.org/ftp/python/%VERSION%/python-%VERSION%-embed-amd64.zip"
set "ZIP=%INSTALL_DIR%\tmp.zip"
set "PYTHON_EXE=%INSTALL_DIR%\python.exe"

echo Installing embedded Python %VERSION%...
echo ======================================
echo.

if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
mkdir "%INSTALL_DIR%"
if errorlevel 1 goto :error_exit

curl -L --fail -o "%ZIP%" "%URL%"
if errorlevel 1 (
    echo Download failed.
    goto :error_exit
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%INSTALL_DIR%' -Force"
if errorlevel 1 (
    echo Extraction failed.
    goto :error_exit
)

if exist "%ZIP%" del "%ZIP%"

exit /b 0

:usage
echo [Error] Usage: %~nx0 ^<version^> ^<install-dir^>
exit /b 2

:refuse_script_dir_or_parent
echo [Error] Refusing to delete the generic helper directory or one of its parents.
goto :error_exit

:error_exit
if defined PYTHON_EXE del "%PYTHON_EXE%" > nul 2>&1
echo [Error] Embedded Python installation failed.
exit /b 1

:is_script_dir_or_parent
set "CHECK_DIR=%~2"
:check_parent
if /i "%~1"=="%CHECK_DIR%" exit /b 1
for %%I in ("%CHECK_DIR%\..") do set "PARENT_DIR=%%~fI"
if /i "%PARENT_DIR%"=="%CHECK_DIR%" exit /b 0
set "CHECK_DIR=%PARENT_DIR%"
goto :check_parent
