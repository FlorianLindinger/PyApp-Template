@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Like list_packages, plus the newer versions on PyPI and which ones the limits allow (needs internet).
call "%~dp0..\DONT_CHANGE\B\run.bat" dev list-packages --outdated %*
exit /b %ERRORLEVEL%
