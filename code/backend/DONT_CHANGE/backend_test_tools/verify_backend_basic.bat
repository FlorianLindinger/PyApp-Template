@echo off
setlocal

py -3 "%~dp0helper_scripts\verify_backend.py" basic
exit /b %ERRORLEVEL%
