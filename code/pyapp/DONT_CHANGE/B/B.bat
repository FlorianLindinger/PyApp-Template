@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem The browser terminal shortcut: like W.bat, but the program runs in a terminal in the browser.
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
set "PYAPP_LAUNCH_MODE=browser"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\start_program.py"
call "%~dp0..\bootstrap\run.bat" %*
exit /b %ERRORLEVEL%
