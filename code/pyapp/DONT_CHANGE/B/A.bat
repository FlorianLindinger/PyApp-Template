@echo off
rem A.bat: prepares the batch entry points that Setup writes into batch_shortcuts\ (setting
rem generate_batch_shortcuts_for_args_launch). Those files stay behind when a project updates by
rem replacing DONT_CHANGE, so this is the only launcher path they name (PROTECTED_PATHS in
rem pyapp_settings.py); everything it points to may move between versions.
rem Called with CALL and without arguments: the user's arguments stay in the calling file, which
rem passes them to Python itself, because every extra batch file would parse them again.
rem No setlocal: the variables below must reach the caller. ensure_runtime.bat sets PYAPP_PYTHON.
call "%~dp0..\scripts\bootstrap\ensure_runtime.bat"
if errorlevel 1 exit /b 1
rem "for %%F in (...)" with one item turns "a\..\b" into a clean full path (%%~fF).
for %%F in ("%~dp0..\scripts\entrypoint.py") do set "PYAPP_ENTRYPOINT=%%~fF"
for %%F in ("%~dp0..\scripts\actions\start_program.py") do set "PYAPP_START_PROGRAM=%%~fF"
exit /b 0
