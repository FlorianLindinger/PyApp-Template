@echo off
setlocal

cd /d "%~dp0"
call generate_icons_standalone\run.exe

echo.
echo Press any key to exit
pause > nul
