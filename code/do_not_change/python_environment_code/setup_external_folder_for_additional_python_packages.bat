@echo off
setlocal

REM === CONFIGURE THESE ===
set "base_venv_path=python_environment"
set "installed_packages_path=installed_python_packages"
CALL :make_absolute_path_if_relative %base_venv_path%
SET "base_venv_path=%OUTPUT%"
CALL :make_absolute_path_if_relative %installed_packages_path%
SET "installed_packages_path=%OUTPUT%"

REM === 1) Ensure external folder exists ===
if not exist "%installed_packages_path%" (
    echo Creating folder: %installed_packages_path%
    mkdir "%installed_packages_path%"
)

REM === 2) Add .pth into base_venv_path site-packages ===
set "PTHFILE=%base_venv_path%\Lib\site-packages\external.pth"
echo %installed_packages_path%>"%PTHFILE%"
echo Created %PTHFILE% that points to %installed_packages_path%

REM === 3) Patch activate.bat to set PIP_TARGET ===
set "ACTIVATE=%base_venv_path%\Scripts\activate.bat"
findstr /c:"PIP_TARGET" "%ACTIVATE%" >nul
if errorlevel 1 (
    echo.>>"%ACTIVATE%"
    echo @REM === auto-added for external packages ===>>"%ACTIVATE%"
    echo @SET "PIP_TARGET=%installed_packages_path%">>"%ACTIVATE%"
    echo Patched activate.bat to export PIP_TARGET
) else (
    echo activate.bat already has PIP_TARGET
)
endlocal


pause

EXIT /B


@REM -------------------------------------------------
@REM function that makes relative path (relative to current working directory) to absolute if not already:
@REM -------------------------------------------------
:make_absolute_path_if_relative
	SET "OUTPUT=%~f1"
	GOTO :EOF
@REM -------------------------------------------------

