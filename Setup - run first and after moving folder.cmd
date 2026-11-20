@echo off
rem Setup: prepares uv, Python and the packages, then creates the shortcuts for this folder.
rem The work is done by code/pyapp/DONT_CHANGE/actions/setup.py; this file starts it and keeps the
rem window open at the end. Batch basics are explained in code/pyapp/DONT_CHANGE/B/W.bat.
setlocal EnableExtensions DisableDelayedExpansion
:: This outer window owns the final prompt, even if the child shell exits.
set "PYAPP_ENTRYPOINT_NO_PAUSE=1"
rem Run Setup in a second command interpreter (%ComSpec% is cmd.exe): even if something in it
rem closes its shell, this window survives to show the result. The ^" marks keep the inner quotes.
"%ComSpec%" /d /s /c ^""%~dp0code\pyapp\DONT_CHANGE\B\run.bat" setup^"
set "setup_exit_code=%ERRORLEVEL%"
:: setup.py prints the success message itself; a failure may happen before Python runs.
rem Get the ESC character into the variable esc; ESC sequences such as [1;37;41m color the text.
for /f %%e in ('echo prompt $E^| cmd /d') do set "esc=%%e"
if not "%setup_exit_code%"=="0" (
    echo.
    echo %esc%[1;37;41m ERROR %esc%[0m Setup failed. Exit code: %setup_exit_code%
    echo Review the messages above before trying again.
)
echo.
echo %esc%[90mPress any key to close this setup window.%esc%[0m
rem pause waits for a key; "> nul" hides its "Press any key" text, which is printed above instead.
pause > nul
exit /b %setup_exit_code%
