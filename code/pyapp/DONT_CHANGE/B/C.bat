@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem C.bat: what the "(Crash-Logs)" shortcut runs: opens the crash log folder in Explorer.
rem See W.bat for the batch basics. The Python action reads crash_log_path from the settings on
rem every click, so the shortcut follows the setting without running Setup again. (Shortcuts made
rem by earlier versions pass the folder as %1; it is ignored.)
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\actions\open_folder.py"
call "%~dp0..\scripts\bootstrap\run.bat" crash_logs
exit /b %ERRORLEVEL%
