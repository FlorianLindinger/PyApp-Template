@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Setup passes the crash log folder: open it without Python. Otherwise (a path relative to
rem the start folder, or with date codes) the Python action resolves it.
call "%~dp0..\bootstrap\open_folder.bat" %1 && exit /b 0
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\open_folder.py"
call "%~dp0..\bootstrap\run.bat" crash_logs
exit /b %ERRORLEVEL%
