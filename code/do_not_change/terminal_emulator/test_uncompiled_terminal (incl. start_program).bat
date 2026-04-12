@echo off

:start

..\P\P.exe "..\specific_scripts\start_program.py" "pyapp-template" "1" "uncompiled"

:: it won't wait after launch of terminal since start_program.py exits

echo.
echo Press any key to (re)open terminal
pause > nul
cls
goto start