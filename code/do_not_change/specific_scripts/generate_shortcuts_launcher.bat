@echo off
setlocal
cd /d "%~dp0"

:: ===========================

set "python_exe=..\P\P.exe"
set "shortcut_generator_script=generate_shortcuts.py"

:: ===========================

:: install backend python if not already installed. This will also install pip and the packages
if not exist "%python_exe%" (
    call "install_backend_python.bat"
) 

:: abort if error
if errorlevel 1 (
    del "%python_exe%" > nul 2>&1
    echo [Error] Backend Python installation failed. Aborting. Press any key to exit.
    pause > nul
    exit 1
)

:: generate shortcuts
"%python_exe%" "%shortcut_generator_script%"

:: THIS PART OF THE CODE SHOULD NOT BE REACHED SINCE shortcut_generator_script SHOULD KILL THE TERMINAL
echo [Error] Shortcut generation failed. Aborting. Press any key to exit.
pause > nul
exit 1