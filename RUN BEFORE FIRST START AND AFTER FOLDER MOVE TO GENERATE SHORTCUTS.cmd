@REM : This line is hidden with @ because echo is still enabled before @echo off.
@REM : @echo off stops cmd.exe from printing every command before it runs it.
@echo off

REM : setlocal keeps environment changes inside this batch file.
REM : Without it, variables or directory changes could leak into the caller shell.
setlocal

REM : %~dp0 expands to the drive and folder of this .cmd file.
REM : cd /d changes to that folder and also switches drives when needed.
REM : This makes all relative paths below resolve from the repository root.
cd /d "%~dp0"

REM : call runs another batch file and then returns here after it finishes.
REM : The called setup batch installs backend Python if missing and runs the
REM : shortcut generator that creates the real local .lnk files with icons.
call "code\backend\DONT_CHANGE\scripts\setup\generate_shortcuts_launcher.bat"

REM : %ERRORLEVEL% is the exit code from the called setup/generator batch.
REM : exit /b returns that same code to the terminal or parent process.
exit /b %ERRORLEVEL%
