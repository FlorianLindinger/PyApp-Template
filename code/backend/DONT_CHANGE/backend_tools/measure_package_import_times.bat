:: Description: Measures startup overhead for selected backend packages directly.
::
:: ===========================

:: disable printing of commands:
@echo off

:: make variables local:
setlocal

:: move to folder of this file:
cd /d "%~dp0"

:: ===========================
:: local variables

set "ensure_backend_python_script=..\B\helper_scripts\ensure_backend_python.bat"
set "modules=os sys subprocess shutil rich traceback ctypes time re tempfile html.parser urllib.parse urllib.request urllib.error uuid signal threading"

:: ===========================
:: code execution

call "%ensure_backend_python_script%"
if errorlevel 1 exit /b 1
for %%M in (%modules%) do "%python_exe%" -c "import %%M"
exit /b %ERRORLEVEL%
exit /b %ERRORLEVEL%
