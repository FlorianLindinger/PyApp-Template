:: Description: Applies safe Ruff fixes, then runs default main.py verification.
@echo off
call "%~dp0verify_main_py.bat" --fix %*
exit /b %ERRORLEVEL%
