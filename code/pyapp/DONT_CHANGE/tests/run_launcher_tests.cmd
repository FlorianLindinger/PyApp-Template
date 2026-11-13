@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Run the launcher's regression tests (DONT_CHANGE/tests, code in src); optional groups or file patterns, e.g. browser or test_wrapper.py.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\dev_tools\main.py"
call "%~dp0..\bootstrap\run.bat" test %*
exit /b %ERRORLEVEL%
