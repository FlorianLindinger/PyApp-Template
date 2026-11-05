@echo off
setlocal EnableExtensions DisableDelayedExpansion
echo Prepares uv, Python and the app's packages, then creates or updates the shortcuts.
echo Run this again after moving or renaming the project folder or a parent folder.
echo.
:: This outer window owns the final prompt, even if the child shell exits.
set "PYAPP_ENTRYPOINT_NO_PAUSE=1"
set "PYAPP_ALLOW_DOWNLOADS=1"
set "PYAPP_ENTRY_SCRIPT=%~dp0code\backend\DONT_CHANGE\setup\generate_shortcuts.py"
"%ComSpec%" /d /s /c ""%~dp0code\backend\DONT_CHANGE\bootstrap\run.bat""
set "setup_exit_code=%ERRORLEVEL%"
echo.
if "%setup_exit_code%"=="0" (
    echo [Success] Setup completed. Shortcuts are ready for this location.
) else (
    echo [Error] Setup failed or crashed. Exit code: %setup_exit_code%
    echo Review the error messages above before trying again.
)
echo.
echo Press any key to close this setup window.
pause > nul
exit /b %setup_exit_code%
