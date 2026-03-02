@echo off

:start

compiled\run.exe "..\..\main_code.py" "..\..\py_env\virt_env\portable_Scripts\python.bat" "Test Title" "..\..\icons\icon.ico" "pyapp-template"

echo.
echo Press any key to reopen...
pause > nul
cls
goto start