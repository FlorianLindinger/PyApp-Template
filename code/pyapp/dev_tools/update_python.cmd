@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Newest patch of the project's Python (and newest minor for python_version = "").
call "%~dp0..\DONT_CHANGE\run.bat" dev update-python %*
exit /b %ERRORLEVEL%
