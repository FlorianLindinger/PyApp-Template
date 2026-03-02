@echo off

:start

py terminal_emulator.py "..\..\main_code.py" "..\..\py_env\virt_env\portable_Scripts\python.bat" "Test Title" "..\..\icons\icon.ico" "pyapp-template"

echo.
echo Press any key to reopen...
pause > nul
cls
goto start