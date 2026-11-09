@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Find the packages the code imports and add the missing ones after review.
call "%~dp0..\DONT_CHANGE\run.bat" dev find-imports %*
exit /b %ERRORLEVEL%
