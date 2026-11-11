@echo off
setlocal EnableExtensions DisableDelayedExpansion
for /f %%e in ('echo prompt $E^| cmd /d') do set "esc=%%e"
echo Opens the icon customization instructions in Notepad.
echo.
call "%~dp0..\DONT_CHANGE\run.bat" icons-help
set "help_exit_code=%ERRORLEVEL%"
if "%help_exit_code%"=="0" (
    echo %esc%[1;37;42m OK %esc%[0m The icon instructions are open in Notepad.
    powershell.exe -NoLogo -NoProfile -NonInteractive -Command "3..1 | ForEach-Object { Write-Host -NoNewline (\"`rThis window closes in $_ s ...\") -ForegroundColor DarkGray; Start-Sleep -Seconds 1 }"
    exit /b 0
)
echo %esc%[1;37;41m ERROR %esc%[0m Could not open the instructions. Exit code: %help_exit_code%
echo.
echo %esc%[90mPress any key to close this window.%esc%[0m
pause > nul
exit /b %help_exit_code%
