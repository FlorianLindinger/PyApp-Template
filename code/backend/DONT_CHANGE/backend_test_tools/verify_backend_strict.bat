@echo off
setlocal

py -3 "%~dp0helper_scripts\verify_backend.py" strict
exit /b %ERRORLEVEL%
