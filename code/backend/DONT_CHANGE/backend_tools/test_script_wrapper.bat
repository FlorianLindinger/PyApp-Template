:: Description: Starts the frontend script wrapper directly with supplied arguments.
::
:: ===========================

:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: move to folder of this file:
cd /d "%~dp0"

:: ===========================
:: local variables

set "target_script=..\scripts\shortcut_targets\childs\frontend_python\script_wrapper.py"

:: ===========================
:: code execution

py -3 "%target_script%" %*
exit /b %ERRORLEVEL%
