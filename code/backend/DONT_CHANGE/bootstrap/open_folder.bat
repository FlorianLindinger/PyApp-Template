@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Opens folder %1 in Explorer without starting Python; creates it if needed. Setup passes the
rem resolved log folder as the shortcut argument. Exit code 1 = no usable folder was passed, the
rem calling B\*.bat then lets the Python action resolve the folder.
if "%~1"=="" exit /b 1
if not exist "%~1\" mkdir "%~1" 2>nul
if not exist "%~1\" exit /b 1
start "" explorer.exe "%~1"
exit /b 0
