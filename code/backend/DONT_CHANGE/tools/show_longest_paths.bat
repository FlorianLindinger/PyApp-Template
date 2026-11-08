@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Prints the longest paths (files and folders, including ignored ones such as generated\.venv
rem and __pycache__ files that do not exist yet)
rem in this project, their length, and whether they exceed the classic
rem Windows path limit (MAX_PATH). Junctions/symlinks are listed but not followed; .git is skipped.
rem Usage: show_longest_paths.bat [count=30] [folder=this project]
:start
for %%I in ("%~dp0..\..\..\..") do set "PYAPP_LP_ROOT=%%~fI"
if not "%~2"=="" set "PYAPP_LP_ROOT=%~f2"
set "PYAPP_LP_COUNT=30"
if not "%~1"=="" set "PYAPP_LP_COUNT=%~1"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\tools\show_longest_paths.ps1"
echo.
echo Press any key to remeasure 
pause > nul
cls
goto :start
exit /b
