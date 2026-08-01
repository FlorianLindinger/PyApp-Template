:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: move to folder of this file:
cd /d "%~dp0"


:: ===========================
:: local variables

set "backend_python_exe=..\..\backend_python\python.exe"
set "install_backend_script=..\..\scripts\setup\install_backend_python.bat"

:: ===========================
:: code execution

:: convert rel path to abs:
for %%I in ("%backend_python_exe%") do set "backend_python_exe=%%~fI"

:: install backend Python if not already installed. This also installs pip and the packages:
if exist "%backend_python_exe%" goto :success

:: error handling and exit is also inside the installer:
call "%install_backend_script%"
if errorlevel 1 goto :failure
if not exist "%backend_python_exe%" goto :failure

:success
:: setlocal would normally hide this value; explicitly return it to the parent batch:
endlocal & set "python_exe=%backend_python_exe%"
exit /b 0

:failure
echo [Error] Backend Python installation failed. Aborting. Press any key to exit.
pause > nul
endlocal
exit /b 1
