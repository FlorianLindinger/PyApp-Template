@echo off
setlocal EnableExtensions DisableDelayedExpansion
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ensure_backend_python.ps1"
if errorlevel 1 exit /b 1
for %%I in ("%~dp0..\..\backend_python\python.exe") do set "backend_python_exe=%%~fI"
endlocal & set "python_exe=%backend_python_exe%"
exit /b 0
