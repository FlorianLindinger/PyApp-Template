@echo off
setlocal EnableExtensions DisableDelayedExpansion
for /f %%e in ('echo prompt $E^| cmd /d') do set "esc=%%e"
echo Regenerates this project's ICO files from icon.png. Asks before replacing an ICO you placed yourself.
echo.
:: Keep this window alive even if the generator's child shell exits.
set "PYAPP_ENTRYPOINT_NO_PAUSE=1"
"%ComSpec%" /d /s /c ^""%~dp0..\DONT_CHANGE\run.bat" icons^"
set "icon_exit_code=%ERRORLEVEL%"
echo.
if "%icon_exit_code%"=="0" (
    echo %esc%[1;37;42m OK %esc%[0m Icons regenerated.
) else (
    echo %esc%[1;37;41m ERROR %esc%[0m Icon generation failed. Exit code: %icon_exit_code%
    echo Review the messages above before trying again.
)
echo.
echo %esc%[90mPress any key to close this window.%esc%[0m
pause > nul
exit /b %icon_exit_code%
