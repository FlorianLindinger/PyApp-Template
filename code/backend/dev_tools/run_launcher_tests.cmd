@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Run the launcher's regression tests (DONT_CHANGE/tests); optional file pattern, e.g. test_wrapper.py.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" test %*
exit /b %ERRORLEVEL%
