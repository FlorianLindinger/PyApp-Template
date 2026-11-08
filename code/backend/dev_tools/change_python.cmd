@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Set a new python_version and migrate the project.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\DONT_CHANGE\scripts\dev_tools.py"
call "%~dp0..\DONT_CHANGE\bootstrap\run.bat" change-python %*
exit /b %ERRORLEVEL%
