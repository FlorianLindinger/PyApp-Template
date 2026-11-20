@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem S.bat: what the "(Settings)" shortcut runs. See W.bat for the batch basics.
rem %1 is the first argument: Setup puts the full path of code\settings.py into the shortcut.
rem Setup passes the user settings file: open it without Python; the Python action reports
rem a disabled or missing settings file.
rem "&&" runs the next command only if the one before succeeded (exit code 0). So: if the
rem fast path could open the file, stop here; otherwise continue below and let Python explain why not.
call "%~dp0..\bootstrap\open_file.bat" %1 && exit /b 0
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
rem Slow path: Python finds the file from developer_settings.py and says what is wrong.
rem cd /d changes the current folder, also to another drive (/d).
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\open_file.py"
call "%~dp0..\bootstrap\run.bat" settings
exit /b %ERRORLEVEL%
