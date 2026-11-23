@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem M.bat: what the "(Edit-Code)" shortcut runs: opens the main script in VS Code, or Notepad.
rem See W.bat for the batch basics. The Python action reads main_script_path from the settings on
rem every click, so the shortcut follows the setting without running Setup again. (Shortcuts made
rem by earlier versions pass the file as %1; it is ignored.)
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
rem cd /d changes the current folder, also to another drive (/d).
cd /d "%~dp0"
set "PYAPP_ENTRY_SCRIPT=%~dp0..\scripts\actions\open_file.py"
call "%~dp0..\scripts\bootstrap\run.bat" open_code
exit /b %ERRORLEVEL%
