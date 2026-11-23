@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem The one file the scripts outside DONT_CHANGE start (setup, dev tools, icons), because those
rem scripts stay behind when a project updates by replacing that folder. It lives in B with the
rem shortcut targets: like them, its path must stay the same (PROTECTED_PATHS in pyapp_settings.py).
rem   run.bat setup | icons | icons-help | dev [command] [arguments]
rem See W.bat for the batch basics. %~1 is the first argument without surrounding quotes;
rem "if /i" compares without caring about upper or lower case. Each line below picks the launcher
rem Python file for one command; an unknown command leaves the variable empty.
set "PYAPP_ENTRY_SCRIPT="
if /i "%~1"=="setup" set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\actions\setup.py"
if /i "%~1"=="icons" set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\actions\gen_icons.py"
if /i "%~1"=="dev" set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\dev_tools\main.py"
if /i "%~1"=="icons-help" goto icons_help
rem "goto label" jumps to the line ":label" further down.
if not defined PYAPP_ENTRY_SCRIPT goto unknown
rem The command word itself is passed on too; the Python tool reads its own arguments after it.
call "%~dp0..\scripts\bootstrap\run.bat" %*
exit /b %ERRORLEVEL%

:icons_help
rem The instructions are code\pyapp\icons\README.md; open it in Notepad.
start "" "%SystemRoot%\System32\notepad.exe" "%~dp0..\..\icons\README.md"
exit /b 0

:unknown
echo ERROR  Unknown command. Use: run.bat setup, icons, icons-help or dev [command].
exit /b 2
