@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Runs all of the app's own tests (this folder) with the app's Python.
rem The launcher's tests are not included: they belong to the template, not to your app.
rem Arguments go to pytest or unittest, e.g. -k name -v. Batch basics: see ../pyapp/DONT_CHANGE/B/W.bat.
rem The window stays open at the end, so the result can be read after a double-click.
set "PYAPP_ENTRYPOINT_NO_PAUSE=1"
call "%~dp0..\pyapp\DONT_CHANGE\B\run.bat" dev run-tests %*
set "tests_exit_code=%ERRORLEVEL%"
rem Get the ESC character into the variable esc; ESC sequences such as [1;37;41m color the text.
for /f %%e in ('echo prompt $E^| cmd /d') do set "esc=%%e"
echo.
if "%tests_exit_code%"=="0" (
    echo %esc%[1;30;42m OK %esc%[0m All app tests passed.
) else (
    echo %esc%[1;37;41m FAILED %esc%[0m Some app tests failed. See above.
)
echo.
echo %esc%[90mPress any key to close this window.%esc%[0m
pause > nul
exit /b %tests_exit_code%
