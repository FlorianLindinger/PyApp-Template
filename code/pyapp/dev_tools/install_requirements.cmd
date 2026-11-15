@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Import a requirements file with uv add -r (asks for its path if not supplied).
call "%~dp0..\DONT_CHANGE\B\run.bat" dev install-requirements %*
exit /b %ERRORLEVEL%
