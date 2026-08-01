:: Description: Applies safe Ruff fixes, then runs strict main.py verification.
@echo off
call "%~dp0verify_main_py_strict.bat" --fix %*
exit /b %ERRORLEVEL%
