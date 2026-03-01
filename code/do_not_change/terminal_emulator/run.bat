@echo off

:start

py terminal_emulator.py test.py

echo.
echo Press any key to reopen...
pause > nul
cls
goto start

