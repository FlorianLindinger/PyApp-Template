@echo off
setlocal EnableExtensions DisableDelayedExpansion
echo Opens the icon customization instructions in Notepad.
echo.
set "instructions=%~dp0..\DONT_CHANGE\icon_related\HOW_TO_CHANGE_ICONS.txt"
if not exist "%instructions%" (
    echo [Error] Cannot find the icon instructions:
    echo "%instructions%"
    set "help_exit_code=2"
    goto result
)
"%ComSpec%" /d /s /c ""%SystemRoot%\System32\notepad.exe" "%instructions%""
set "help_exit_code=%ERRORLEVEL%"
:result
echo.
if "%help_exit_code%"=="0" (
    echo [Success] Icon instructions opened in Notepad.
) else (
    echo [Error] Could not open the instructions. Exit code: %help_exit_code%
)
echo.
echo Press any key to close this window.
pause > nul
exit /b %help_exit_code%
