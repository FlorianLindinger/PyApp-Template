@echo off
setlocal EnableExtensions DisableDelayedExpansion
:: This outer window owns the final prompt, even if the child shell exits.
set "PYAPP_ENTRYPOINT_NO_PAUSE=1"
"%ComSpec%" /d /s /c ^""%~dp0code\pyapp\DONT_CHANGE\run.bat" setup^"
set "setup_exit_code=%ERRORLEVEL%"
:: setup.py prints the success message itself; a failure may happen before Python runs.
for /f %%e in ('echo prompt $E^| cmd /d') do set "esc=%%e"
if not "%setup_exit_code%"=="0" (
    echo.
    echo %esc%[1;37;41m ERROR %esc%[0m Setup failed. Exit code: %setup_exit_code%
    echo Review the messages above before trying again.
)
echo.
echo %esc%[90mPress any key to close this setup window.%esc%[0m
pause > nul
exit /b %setup_exit_code%
