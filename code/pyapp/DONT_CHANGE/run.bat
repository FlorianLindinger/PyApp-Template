@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem The one file that scripts outside DONT_CHANGE start, because those scripts stay behind when a
rem project updates by replacing this folder. Everything else in here can move between versions.
rem   run.bat setup | icons | icons-help | dev [command] [arguments]
set "PYAPP_ENTRY_SCRIPT="
if /i "%~1"=="setup" set "PYAPP_ENTRY_SCRIPT=%~dp0actions\setup.py"
if /i "%~1"=="icons" set "PYAPP_ENTRY_SCRIPT=%~dp0actions\gen_icons.py"
if /i "%~1"=="dev" set "PYAPP_ENTRY_SCRIPT=%~dp0scripts\dev_tools\main.py"
if /i "%~1"=="icons-help" goto icons_help
if not defined PYAPP_ENTRY_SCRIPT goto unknown
call "%~dp0bootstrap\run.bat" %*
exit /b %ERRORLEVEL%

:icons_help
start "" "%SystemRoot%\System32\notepad.exe" "%~dp0data\icons\HOW_TO_CHANGE_ICONS.txt"
exit /b %ERRORLEVEL%

:unknown
echo ERROR  Unknown command. Use: run.bat setup, icons, icons-help or dev [command].
exit /b 2
