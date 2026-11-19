@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Run all tests: the app's own (code\tests, code\pyapp\tests), then the launcher's if they are there.
rem Arguments go to the app tests (pytest or unittest, e.g. -k name -v).
set "PYAPP_ENTRYPOINT_NO_PAUSE=1"
set "failed="
call "%~dp0..\DONT_CHANGE\B\run.bat" dev run-tests %*
if errorlevel 1 set "failed=1"
if exist "%~dp0..\DONT_CHANGE\tests\" (
    call "%~dp0..\DONT_CHANGE\B\run.bat" dev test
    if errorlevel 1 set "failed=1"
)
for /f %%e in ('echo prompt $E^| cmd /d') do set "esc=%%e"
echo.
if defined failed (
    echo %esc%[1;37;41m FAILED %esc%[0m Some tests failed. See above.
) else (
    echo %esc%[1;30;42m OK %esc%[0m All tests passed.
)
echo.
echo %esc%[90mPress any key to close this window.%esc%[0m
pause > nul
if defined failed exit /b 1
exit /b 0
