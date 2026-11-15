@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Review imports, then replace the package declarations and sync.
call "%~dp0..\DONT_CHANGE\B\run.bat" dev reset-imports %*
exit /b %ERRORLEVEL%
