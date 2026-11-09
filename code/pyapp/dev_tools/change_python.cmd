@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Set a new python_version and migrate the project.
call "%~dp0..\DONT_CHANGE\run.bat" dev change-python %*
exit /b %ERRORLEVEL%
