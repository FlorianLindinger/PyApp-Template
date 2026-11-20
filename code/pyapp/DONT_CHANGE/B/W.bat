@echo off
rem ==============================================================================================
rem W.bat: what the main shortcut "<program name>" runs. W = with a terminal (console) window.
rem
rem What happens when someone double-clicks that shortcut:
rem   1. This file writes down HOW the app should start (in a terminal) and WHICH launcher
rem      Python file does the start (actions\start_program.py).
rem   2. bootstrap\run.bat makes sure uv and a Python exist (bootstrap\ensure_runtime.bat) and
rem      runs that Python file with it.
rem   3. start_program.py checks the settings, installs the packages if needed and starts
rem      runtime\bg_watchdog.py, which runs code\main.py and takes care of the window, the log
rem      and the crash report.
rem The other files in this folder (N, B, S, Q, L, C, M) work the same way for the other shortcuts.
rem
rem Batch basics, used in every .bat and .cmd file of the launcher:
rem   @echo off         Do not print each command before running it. The @ hides this line too.
rem   rem ...           A comment: Windows ignores the rest of the line.
rem   setlocal          Variables set after this disappear when the file ends, so nothing leaks
rem                     into the window that started it. EnableExtensions turns on the modern
rem                     forms of commands; DisableDelayedExpansion keeps a "!" in a folder name
rem                     from being read as a variable.
rem   set "NAME=value"  Creates a variable. Writing its name between percent signs later inserts
rem                     its value. Quoting the whole assignment keeps stray spaces out of it.
rem   if not defined X  True when the variable X does not exist yet.
rem   %~dp0             The folder this .bat file is in, ending with a backslash (d = drive,
rem                     p = path, 0 = this file). Paths built from it work wherever the project is.
rem   ..                The parent folder, so "%~dp0..\actions" is DONT_CHANGE\actions.
rem   %CD%              The current folder; for a shortcut, the "Start in" folder Windows chose.
rem   %*                All arguments this file received, passed on unchanged.
rem   call "x.bat"      Runs another batch file and continues here when it ends.
rem   exit /b N         Ends this file (not the window) with exit code N; 0 means success.
rem   %ERRORLEVEL%      The exit code of the last program or batch file that ran.
rem ==============================================================================================
setlocal EnableExtensions DisableDelayedExpansion
rem Remember the folder the user started from, unless a calling file already did.
if not defined PYAPP_START_DIR set "PYAPP_START_DIR=%CD%"
rem "terminal": show the app in a console window (Windows Terminal or the classic console).
set "PYAPP_LAUNCH_MODE=terminal"
rem The launcher's Python file that does the start; bootstrap\run.bat runs it.
set "PYAPP_ENTRY_SCRIPT=%~dp0..\actions\start_program.py"
rem Hand over to the shared bootstrap and pass on the arguments (Setup puts the app's ID there).
call "%~dp0..\bootstrap\run.bat" %*
rem Pass the result on, so whoever started this file can see success or failure.
exit /b %ERRORLEVEL%
