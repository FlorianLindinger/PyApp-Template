@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Opens the compilation menu: presets, Windows build, Linux build, clean up.
rem The settings are the .json files in this folder; see README.md. Batch basics: see ../DONT_CHANGE/B/W.bat.
call "%~dp0..\DONT_CHANGE\B\run.bat" dev compilation %*
exit /b %ERRORLEVEL%
