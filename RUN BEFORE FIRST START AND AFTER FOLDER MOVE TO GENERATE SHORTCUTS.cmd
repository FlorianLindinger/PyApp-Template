@rem This line is hidden with @ because echo is still enabled before @echo off.
@rem @echo off stops cmd.exe from printing every command before it runs it.
@echo off

rem setlocal keeps environment changes inside this batch file.
rem Without it, variables or directory changes could leak into the caller shell.
setlocal

rem %~dp0 expands to the drive and folder of this .cmd file.
rem cd /d changes to that folder and also switches drives when needed.
rem This makes all relative paths below resolve from the repository root.
cd /d "%~dp0"

rem call runs another batch file and then returns here after it finishes.
rem The called setup batch installs backend Python if missing and runs the
rem shortcut generator that creates the real local .lnk files with icons.
call "code\backend\DONT_CHANGE\scripts\setup\generate_shortcuts_launcher.bat"

rem %ERRORLEVEL% is the exit code from the called setup/generator batch.
rem exit /b returns that same code to the terminal or parent process.
exit /b %ERRORLEVEL%
