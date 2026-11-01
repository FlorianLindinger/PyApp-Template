@echo off
setlocal EnableExtensions DisableDelayedExpansion
echo Regenerates this project's ICO files from the configured PNG images.
echo.
:: Keep this window alive even if the generator's child shell exits.
set "PYAPP_ENTRYPOINT_NO_PAUSE=1"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\actions\generate_icons.py"
"%ComSpec%" /d /s /c ""%~dp0..\DONT_CHANGE\scripts\setup\run_backend_script.bat""
set "icon_exit_code=%ERRORLEVEL%"
echo.
if "%icon_exit_code%"=="0" (
    echo [Success] Icons regenerated.
) else (
    echo [Error] Icon generation failed or crashed. Exit code: %icon_exit_code%
    echo Review the error messages above before trying again.
)
echo.
echo Press any key to close this window.
pause > nul
exit /b %icon_exit_code%
