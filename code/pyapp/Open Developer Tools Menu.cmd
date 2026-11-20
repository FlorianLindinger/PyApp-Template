@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Double-click: a numbered menu of every developer tool.
rem With a command it runs that tool directly, e.g. from a terminal in this folder:
rem   "Open Developer Tools Menu.cmd" add requests numpy
rem   "Open Developer Tools Menu.cmd" sync
rem   "Open Developer Tools Menu.cmd" compile-app --preset gui
rem The menu lists every command name. Batch basics: see DONT_CHANGE/B/W.bat.
call "%~dp0DONT_CHANGE\B\run.bat" dev menu %*
exit /b %ERRORLEVEL%
