@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem The one file the scripts outside DONT_CHANGE start (setup, dev tools, icons), because those
rem scripts stay behind when a project updates by replacing that folder. It lives in B with the
rem shortcut targets: like them, its path must stay the same (PROTECTED_PATHS in backend_settings.py).
rem   run.bat setup | icons | icons-help | dev [command] [arguments]
set "PYAPP_ENTRY_SCRIPT="
if /i "%~1"=="setup" set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\setup.py"
if /i "%~1"=="icons" set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\gen_icons.py"
if /i "%~1"=="dev" set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\dev_tools\main.py"
if /i "%~1"=="icons-help" goto icons_help
if not defined PYAPP_ENTRY_SCRIPT goto unknown
call "%~dp0..\bootstrap\run.bat" %*
exit /b %ERRORLEVEL%

:icons_help
rem The instructions are code\pyapp\icons\README.md; a project from before it existed gets the short version.
if exist "%~dp0..\..\icons\README.md" (
    start "" "%SystemRoot%\System32\notepad.exe" "%~dp0..\..\icons\README.md"
    exit /b 0
)
echo To change the icons: replace code\pyapp\icons\icon.png with your picture, run
echo "regenerate icons.cmd" in that folder, then run Setup again for the shortcuts.
echo To use your own icon for one case, replace that .ico file and keep its name.
exit /b 0

:unknown
echo ERROR  Unknown command. Use: run.bat setup, icons, icons-help or dev [command].
exit /b 2
