@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem L.bat: what the "(Logs)" shortcut runs: opens the log folder in Explorer.
rem See W.bat for the batch basics. The Python action reads log_path from the settings on every
rem click, so the shortcut follows the setting without running Setup again. (Shortcuts made by
rem earlier versions pass the folder as %1; it is ignored.)
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\actions\open_folder.py"
call "%~dp0..\scripts\bootstrap\run.bat" logs
exit /b %ERRORLEVEL%
