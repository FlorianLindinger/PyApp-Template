@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Opens folder %1 in Explorer without starting Python; creates it if needed. Setup passes the
rem resolved log folder as the shortcut argument. Exit code 1 = no usable folder was passed, the
rem calling B\*.bat then lets the Python action resolve the folder.
rem %~1 is the first argument without quotes; "" means none was given.
if "%~1"=="" exit /b 1
rem The trailing backslash makes "exist" true only for a folder. 2>nul hides error messages.
if not exist "%~1\" mkdir "%~1" 2>nul
if not exist "%~1\" exit /b 1
rem "start" opens a program without waiting for it; the empty "" is the window title it expects first.
start "" explorer.exe "%~1"
exit /b 0
