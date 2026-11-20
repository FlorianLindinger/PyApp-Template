@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Runs %PYAPP_ENTRY_SCRIPT% (a tool with a main() function) through scripts\entrypoint.py,
rem which applies the shared error and exit policy, with the launcher Python. -I -S: standard library only,
rem so application packages can never break the launcher itself. -X utf8: output and
rem files use UTF-8, so non-ASCII project paths also work when output is redirected.
rem Step 2 of a start (step 1 is a file in B\, see B\W.bat). The calling file set PYAPP_ENTRY_SCRIPT.
rem The lines in parentheses run together, only when the condition is true.
if not defined PYAPP_ENTRY_SCRIPT (
    echo ERROR  Missing launcher entry script.
    set "exit_code=2"
    goto failed
)
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
rem Find uv and the Python that runs the launcher. ensure_runtime.bat leaves their paths in the
rem variables PYAPP_UV and PYAPP_PYTHON. It is quick when nothing changed since the last start.
call "%~dp0ensure_runtime.bat"
rem "if errorlevel 1" is true when the last exit code was 1 or higher, i.e. something failed.
if errorlevel 1 goto bootstrap_failed
rem Now run Python: entrypoint.py loads the entry script, calls its main() and turns errors into
rem readable messages. Everything from here on is Python.
rem After a failure this file, not Python, waits for a key: then the window also stays open when
rem Python itself cannot start or the launcher has a bug that stops it before its own error
rem handling. PYAPP_BATCH_PAUSES_ON_FAILURE tells entrypoint.py not to ask a second time.
set "PYAPP_BATCH_PAUSES_ON_FAILURE=1"
"%PYAPP_PYTHON%" -I -S -X utf8 "%~dp0..\scripts\entrypoint.py" "%PYAPP_ENTRY_SCRIPT%" %*
set "exit_code=%ERRORLEVEL%"
if "%exit_code%"=="0" exit /b 0
goto failed

:bootstrap_failed
set "exit_code=1"

rem Something failed and printed its message already; keep the window open so it can be read.
rem Callers that keep their own window open (Setup, the tests) set PYAPP_ENTRYPOINT_NO_PAUSE=1.
:failed
if "%PYAPP_ENTRYPOINT_NO_PAUSE%"=="1" exit /b %exit_code%
echo.
echo Press any key to close this window.
pause >nul
exit /b %exit_code%
