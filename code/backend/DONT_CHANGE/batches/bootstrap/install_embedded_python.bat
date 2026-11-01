@echo off
setlocal EnableExtensions DisableDelayedExpansion
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0install_embedded_python.ps1" -Version "%~1" -InstallDir "%~2"
exit /b %ERRORLEVEL%
