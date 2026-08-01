:: Description: Applies safe Ruff fixes, then runs basic main.py verification.
@echo off
call "%~dp0verify_main_py_basic.bat" --fix %*
exit /b %ERRORLEVEL%
