@echo off
setlocal

set "PY_VERSION=%~1"
set "TEST_MODE=%~2"

if "%PY_VERSION%"=="" set "PY_VERSION=3"
if "%TEST_MODE%"=="" set "TEST_MODE=all"

set "TEST_DIR=%~dp0"
set "WRAPPER_PATH=%TEST_DIR%..\scripts\frontend\script_wrapper.py"
set "TEST_SCRIPT_PATH=%TEST_DIR%test_main_script.py"
set "BACKEND_PACKAGES_DIR=%TEST_DIR%..\backend_packages"
set "BACKEND_PYTHON_EXE=%TEST_DIR%..\backend_python\python.exe"
set "EMPTY=__EMPTY__"

echo [Info] Python launcher version: %PY_VERSION%
py -%PY_VERSION% -c "import sys; print('[Info] Actual Python:', sys.version)"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [Info] Wrapper: "%WRAPPER_PATH%"
echo [Info] Test script: "%TEST_SCRIPT_PATH%"
echo [Info] Backend Python: "%BACKEND_PYTHON_EXE%"
echo.

if /I "%TEST_MODE%"=="all" (
    call :run_one valueerror
    call :run_one syntaxerror
    call :run_one keyboardinterrupt
    call :run_one baseexception
    call :run_one chained
    exit /b 0
)

call :run_one "%TEST_MODE%"
exit /b %ERRORLEVEL%

:run_one
set "PYAPP_TEMPLATE_TRACEBACK_TEST_MODE=%~1"
echo ================================================================
echo [Info] Running traceback test mode: %PYAPP_TEMPLATE_TRACEBACK_TEST_MODE%
echo ================================================================
py -%PY_VERSION% "%WRAPPER_PATH%" ^
    "%EMPTY%" ^
    "%EMPTY%" ^
    "%EMPTY%" ^
    "true" ^
    "true" ^
    "true" ^
    "%EMPTY%" ^
    "%EMPTY%" ^
    "%EMPTY%" ^
    "%EMPTY%" ^
    "false" ^
    "false" ^
    "false" ^
    "true" ^
    "%EMPTY%" ^
    "Script Wrapper Traceback Test" ^
    "%TEST_SCRIPT_PATH%" ^
    "%EMPTY%" ^
    "%EMPTY%" ^
    "%EMPTY%" ^
    "true" ^
    "%EMPTY%" ^
    "%EMPTY%" ^
    "%BACKEND_PACKAGES_DIR%" ^
    "%BACKEND_PYTHON_EXE%" ^
    "07" ^
    "%EMPTY%" ^
    "%EMPTY%" ^
    "false"
echo.
exit /b 0
