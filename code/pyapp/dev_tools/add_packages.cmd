@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Add packages (asks for names, or pass them: add_packages.cmd requests numpy).
call "%~dp0..\DONT_CHANGE\run.bat" dev add %*
exit /b %ERRORLEVEL%
