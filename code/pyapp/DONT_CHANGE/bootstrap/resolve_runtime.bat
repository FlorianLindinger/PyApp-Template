@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Gets any working uv and Python, then lets resolve_runtime.py do the real work. Called by
rem ensure_runtime.bat when the cache is missing or stale. Only batch and programs built into Windows
rem (curl, tar), because company policies often block PowerShell scripts. No parenthesized blocks with
rem paths in them: a folder such as "Program Files (x86)" would end the block early.
set "stamp=%~1"
set "bootstrap=%~dp0"
set "pyapp=%~dp0..\.."
set "settings=%pyapp%\developer_settings.py"
set "generated=%pyapp%\generated"
set "temporary=%~dp0..\tmp"
set "user_data=%LOCALAPPDATA%"
if not defined user_data set "user_data=%USERPROFILE%\AppData\Local"
rem uv prints UTF-8, and the project may be in a folder with non-ASCII characters.
set "old_codepage="
for /f "tokens=2 delims=:." %%C in ('chcp') do set "old_codepage=%%C"
chcp 65001 >nul
call :main
set "result=%ERRORLEVEL%"
if defined old_codepage chcp %old_codepage% >nul
exit /b %result%

:main
call :read_setting uv_install_if_missing install_mode
call :read_setting python_source python_source
call :read_setting uv_user_python_visible_globally visible
call :find_uv
if defined boot_uv goto have_uv
if /i "%install_mode%"=="never" goto uv_not_allowed
call :download_uv
if errorlevel 1 exit /b 1
:have_uv
call :find_python
if errorlevel 1 exit /b 1
set "PYAPP_BOOT_UV=%boot_uv%"
"%boot_python%" -I -S -X utf8 "%bootstrap%resolve_runtime.py" --stamp "%stamp%"
exit /b %ERRORLEVEL%

:uv_not_allowed
if defined blocked_uv goto uv_blocked
call :error "No usable uv found and uv_install_if_missing = 'never'. Install uv or change the uv settings in developer_settings.py."
exit /b 1

:uv_blocked
call :error_blocked "%blocked_uv%"
exit /b 1

rem ---------------------------------------------------------------- settings

rem read_setting NAME VARIABLE: a top-level one-line setting; the last definition counts, as in Python.
:read_setting
set "%~2="
set "setting_line="
for /f "tokens=1,* delims==" %%A in ('findstr /b /r /c:"%~1 *[:=]" "%settings%" 2^>nul') do set "setting_line=%%B"
if not defined setting_line exit /b 0
set "setting_line=%setting_line:"=%"
set "setting_line=%setting_line:'=%"
for /f "tokens=1 delims= " %%V in ("%setting_line%") do set "%~2=%%V"
if "%~2"=="" exit /b 0
call set "setting_value=%%%~2%%"
if "%setting_value:~0,1%"=="#" set "%~2="
exit /b 0

rem ---------------------------------------------------------------- uv

:find_uv
set "boot_uv="
set "blocked_uv="
call :try_uv "%generated%\uv\uv.exe"
for /f "delims=" %%U in ('where uv.exe 2^>nul') do call :try_uv "%%U"
if defined UV_INSTALL_DIR call :try_uv "%UV_INSTALL_DIR%\uv.exe"
if defined XDG_BIN_HOME call :try_uv "%XDG_BIN_HOME%\uv.exe"
call :try_uv "%USERPROFILE%\.local\bin\uv.exe"
call :try_uv "%USERPROFILE%\.cargo\bin\uv.exe"
call :try_uv "%user_data%\PyApp-Template\uv\uv.exe"
call :try_uv "%user_data%\PyApp-Template\uv-bootstrap\uv.exe"
exit /b 0

:try_uv
if defined boot_uv exit /b 0
if not exist "%~1" exit /b 0
"%~1" --version >nul 2>&1
if errorlevel 1 set "blocked_uv=%~1"
if not errorlevel 1 set "boot_uv=%~1"
exit /b 0

:download_uv
set "curl=%SystemRoot%\System32\curl.exe"
set "tar=%SystemRoot%\System32\tar.exe"
if not exist "%curl%" goto no_tools
if not exist "%tar%" goto no_tools
set "architecture=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "architecture=%PROCESSOR_ARCHITEW6432%"
set "target="
if /i "%architecture%"=="AMD64" set "target=x86_64-pc-windows-msvc"
if /i "%architecture%"=="ARM64" set "target=aarch64-pc-windows-msvc"
if /i "%architecture%"=="x86" set "target=i686-pc-windows-msvc"
if not defined target goto unknown_architecture
set "boot_dir=%user_data%\PyApp-Template\uv-bootstrap"
rmdir /s /q "%boot_dir%" 2>nul
mkdir "%boot_dir%" 2>nul
set "archive=uv-%target%.zip"
set "url=https://github.com/astral-sh/uv/releases/latest/download/%archive%"
echo Downloading uv ...
"%curl%" --fail --location --silent --show-error --proto "=https" --tlsv1.2 --retry 2 --connect-timeout 30 --max-time 300 -o "%boot_dir%\%archive%" "%url%"
if errorlevel 1 goto download_failed
"%curl%" --fail --location --silent --show-error --proto "=https" --tlsv1.2 --retry 2 --connect-timeout 30 --max-time 60 -o "%boot_dir%\%archive%.sha256" "%url%.sha256"
if errorlevel 1 goto download_failed
set "expected="
for /f "usebackq tokens=1" %%H in ("%boot_dir%\%archive%.sha256") do if not defined expected set "expected=%%H"
rem One cmdlet, not a script: this works under script-blocking policies and in Constrained Language Mode.
set "PYAPP_HASH_FILE=%boot_dir%\%archive%"
set "actual="
for /f "usebackq delims=" %%H in (`powershell.exe -NoLogo -NoProfile -NonInteractive -Command "(Get-FileHash -LiteralPath $env:PYAPP_HASH_FILE -Algorithm SHA256).Hash" 2^>nul`) do if not defined actual set "actual=%%H"
rem Only if PowerShell itself is blocked: there is no other way to check a file with Windows' own tools.
if not defined actual for /f "skip=1 delims=" %%H in ('certutil.exe -hashfile "%boot_dir%\%archive%" SHA256 2^>nul') do if not defined actual set "actual=%%H"
if not defined actual goto cannot_check
set "actual=%actual: =%"
if /i not "%expected%"=="%actual%" goto checksum_failed
"%tar%" -xf "%boot_dir%\%archive%" -C "%boot_dir%"
if errorlevel 1 goto unpack_failed
set "boot_uv=%boot_dir%\uv.exe"
"%boot_uv%" --version >nul 2>&1
if not errorlevel 1 exit /b 0
call :error_blocked "%boot_uv%"
set "boot_uv="
exit /b 1

:no_tools
call :error "curl.exe or tar.exe is missing from Windows (they are part of Windows 10 version 1803 and newer). Install uv yourself, or copy a folder made with the make_portable dev tool to this PC."
exit /b 1

:unknown_architecture
call :error "Unsupported Windows architecture '%architecture%' for uv."
exit /b 1

:download_failed
call :error "Could not download uv from github.com. A firewall or proxy may block it. Set HTTPS_PROXY if your company uses a proxy, ask your IT department to allow github.com, or copy a folder made with the make_portable dev tool to this PC."
exit /b 1

:cannot_check
call :error "The uv download could not be checked: both PowerShell and certutil are blocked on this PC. Install uv yourself, or copy a folder made with the make_portable dev tool to this PC."
exit /b 1

:checksum_failed
call :error "The downloaded uv archive does not match its published SHA-256 checksum."
exit /b 1

:unpack_failed
call :error "Could not unpack the uv download."
exit /b 1

rem ---------------------------------------------------------------- a Python to run resolve_runtime.py

:find_python
set "UV_PYTHON="
set "UV_PROJECT="
set "UV_PROJECT_ENVIRONMENT="
set "UV_WORKING_DIR="
set "UV_MANAGED_PYTHON="
set "UV_NO_MANAGED_PYTHON="
set "VIRTUAL_ENV="
set "UV_PYTHON_PREFERENCE="
set "UV_PYTHON_DOWNLOADS=automatic"
set "UV_PYTHON_INSTALL_DIR="
set "UV_PYTHON_INSTALL_BIN=0"
set "UV_PYTHON_INSTALL_REGISTRY=0"
if /i "%visible%"=="True" set "UV_PYTHON_INSTALL_BIN=1"
if /i "%visible%"=="True" set "UV_PYTHON_INSTALL_REGISTRY=1"
if /i "%python_source%"=="local" set "UV_PYTHON_INSTALL_DIR=%generated%\pythons"
if /i "%python_source%"=="local" set "UV_MANAGED_PYTHON=1"
if /i "%python_source%"=="local" set "UV_PYTHON_INSTALL_BIN=0"
if /i "%python_source%"=="local" set "UV_PYTHON_INSTALL_REGISTRY=0"
if /i "%python_source%"=="system" set "UV_PYTHON_PREFERENCE=only-system"
if /i "%python_source%"=="system" set "UV_PYTHON_DOWNLOADS=never"
if not exist "%temporary%\" mkdir "%temporary%" 2>nul
set "found_file=%temporary%\bootstrap_python.txt"
rem Outside the project: uv would otherwise discover the project's own environment.
pushd "%TEMP%" 2>nul
call :query_python
if defined boot_python goto python_found
if /i "%python_source%"=="system" goto no_system_python
set "request="
if exist "%generated%\.python-version" for /f "usebackq eol=# delims=" %%V in ("%generated%\.python-version") do if not defined request set "request=%%V"
if not defined request call :read_setting python_version request
echo Installing Python %request% with uv ...
"%boot_uv%" python install %request%
if errorlevel 1 goto python_install_failed
call :query_python
if not defined boot_python goto python_install_failed
:python_found
popd
"%boot_python%" -I -S -c "" >nul 2>&1
if not errorlevel 1 exit /b 0
call :error_blocked "%boot_python%"
exit /b 1

:query_python
set "boot_python="
"%boot_uv%" python find --no-project ">=3.8" >"%found_file%" 2>nul
if errorlevel 1 exit /b 0
set /p boot_python=<"%found_file%"
del "%found_file%" 2>nul
exit /b 0

:no_system_python
popd
call :error "python_source is 'system', but no Python 3.8 or newer is installed on this PC. Install one, or change python_source in developer_settings.py."
exit /b 1

:python_install_failed
popd
call :error "uv could not install Python '%request%'. A firewall or proxy may block the download from github.com. Ask your IT department to allow it, use a Python they installed with python_source = 'system', or copy a folder made with the make_portable dev tool to this PC."
exit /b 1

rem ---------------------------------------------------------------- messages

:error
set "message=%~1"
rem Through delayed expansion: a path with & in it would otherwise end the echo command.
setlocal EnableDelayedExpansion
echo.
echo  ERROR  !message!
echo.
endlocal
exit /b 0

:error_blocked
call :error "Windows refused to start %~1. A company policy (AppLocker, Windows Defender Application Control) or an antivirus program may block programs in this folder. Ask your IT department to allow it, or use a Python they installed with python_source = 'system' in developer_settings.py."
exit /b 0
