@echo off
rem Q.bat: what the "(STOP)" shortcut runs (Q = quit). It stops every running copy of this app,
rem including programs the app started. See W.bat for the batch basics.
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
rem Work from this folder, so nothing depends on the shortcut's "Start in" folder.
cd /d "%~dp0"
rem actions\stop_program.py finds the running copies in DONT_CHANGE\tmp\running and ends them.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\stop_program.py"
call "%~dp0..\bootstrap\run.bat" %*
exit /b %ERRORLEVEL%
