<<<<<<< HEAD
:: disable printing of commands
@echo off

:: make variables local
setlocal

:: move to folder of this file
=======
:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: move to folder of this file:
>>>>>>> f82a4acb989934bff49b56bdc7577c626a3fa40c
cd /d "%~dp0"

:: ===========================
:: local variables

<<<<<<< HEAD
set "python_exe=..\..\backend_python\python.exe"
set "shortcut_generator_script=generate_shortcuts.py"
set "terminal_title=Generating Shortcuts"
set "install_backend_script=install_backend_python.bat"
=======
set "ensure_backend_python_script=ensure_backend_python.bat"
set "shortcut_generator_script=generate_shortcuts.py"
set "terminal_title=Generating Shortcuts"
>>>>>>> f82a4acb989934bff49b56bdc7577c626a3fa40c

:: ===========================
:: code execution

<<<<<<< HEAD
:: change title
title %terminal_title%

:: install backend python if not already installed. This will also install pip and the packages
if not exist "%python_exe%" (
    :: error handling and exit is inside
    call "%install_backend_script%"
) 

:: generate shortcuts
"%python_exe%" "%shortcut_generator_script%"
set "exit_code=%ERRORLEVEL%"

:: exit if success
=======
:: change title:
title %terminal_title%

:: install backend Python if needed and receive its path in python_exe:
call "%ensure_backend_python_script%"
:: exit on failure (print and confirm close handled in child):
if not "%ERRORLEVEL%"=="0" (
    exit 1
)

:: generate shortcuts:
"%python_exe%" "%shortcut_generator_script%"
set "exit_code=%ERRORLEVEL%"

:: exit if success:
>>>>>>> f82a4acb989934bff49b56bdc7577c626a3fa40c
if "%exit_code%"=="0" (
    exit /b 0
)

<<<<<<< HEAD
:: print and confirm to close on failure
=======
:: print and confirm to close on failure:
>>>>>>> f82a4acb989934bff49b56bdc7577c626a3fa40c
echo [Error] Shortcut generation failed. Aborting. Press any key to exit.
pause > nul
exit /b %exit_code%
