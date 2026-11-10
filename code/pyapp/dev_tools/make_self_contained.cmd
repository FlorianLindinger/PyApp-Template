@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Put uv, Python and packages inside this folder, so it runs offline on other PCs.
call "%~dp0..\DONT_CHANGE\run.bat" dev make-self-contained %*
exit /b %ERRORLEVEL%
