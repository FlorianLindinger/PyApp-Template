@echo off
setlocal EnableExtensions DisableDelayedExpansion
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
set "PYAPP_LAUNCH_MODE=no_terminal"
call "%~dp0..\scripts\setup\ensure_backend_python.bat"
if errorlevel 1 exit /b 1
"%python_exe%" "%~dp0..\scripts\actions\start_program.py" %*
exit /b %ERRORLEVEL%
