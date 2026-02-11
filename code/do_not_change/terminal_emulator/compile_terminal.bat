@echo off
setlocal enableextensions enabledelayedexpansion

REM ============================
REM  Build settings (edit these)
REM ============================
set "PY_VERSION=3.13"
set "VENV_DIR=DO_NOT_SYNC\.venv"
set "SCRIPT=pyside6_terminal.py"
set "EXE_NAME=run"
set "DO_PRUNE=yes"
REM options: attach, force, disable
REM "attach" means that it will print to console if called via console but not open one if called by double click
set "WINDOWS_CONSOLE_MODE=attach"

REM Metadata
set "COMPANY_NAME=Private Project"
set "PRODUCT_NAME=Windows-only Terminal Emulator"
set "FILE_VERSION=0.0.1"
set "PROD_VERSION=0.0.1"
set "FILE_DESC=PySide6 based Windows-only terminal emulator with extra features."
set "COPYRIGHT=Copyright (c) 2026 Florian Lindinger. All rights reserved."

REM uncomment the next line if you have an icon:
rem set "ICON=code\icons\icon.ico"

REM ============================
REM  Create or reuse temp venv
REM ============================
echo Creating/checking temp venv...
if not exist "%VENV_DIR%" (
  echo Venv not found. Creating...
  py -%PY_VERSION% -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo Failed to create venv.
    exit /b 1
  )
  echo Installing build dependencies...
  call "%VENV_DIR%\Scripts\python.exe" -m pip install ^
    nuitka ^
    PySide6-Essentials
  if errorlevel 1 (
    echo Failed to install dependencies.
    exit /b 1
  )
) else (
  echo Reusing existing venv.
)

set "PY=%VENV_DIR%\Scripts\python.exe"

REM ============================
REM  Safety Verification
REM ============================

if "%EXE_NAME%"=="" ( echo ERROR: EXE_NAME variable is empty. Safety halt. & pause & exit /b 1 )

REM Clean output (but keep venv)
if exist "DO_NOT_SYNC\build" (
    echo Cleaning previous build in "DO_NOT_SYNC\build"...
    rmdir /s /q "DO_NOT_SYNC\build"
)

REM ============================
REM  Compile (MINIMAL SIZE + SPEED)
REM  - one-folder (standalone), NOT onefile
REM  - minimal Qt plugins (only qwindows)
REM  - no translations, no QML, no extra libraries
REM  - remove debug info, disable tracing
REM ============================

set "CMD=%PY% -m nuitka"
set "CMD=!CMD! --standalone"
set "CMD=!CMD! --output-dir=DO_NOT_SYNC\build"
set "CMD=!CMD! --output-filename=%EXE_NAME%"
set "CMD=!CMD! --enable-plugin=pyside6"
set "CMD=!CMD! --windows-console-mode=%WINDOWS_CONSOLE_MODE%"

if not "%ICON%"=="" ( set "CMD=!CMD! --windows-icon-from-ico=%ICON%" )

set "CMD=!CMD! --include-qt-plugins=platforms"
set "CMD=!CMD! --python-flag=-OO"
set "CMD=!CMD! --noinclude-qt-translations"
set "CMD=!CMD! --noinclude-default-mode=nofollow"
set "CMD=!CMD! --nofollow-import-to=PySide6.QtQml,PySide6.QtQuick,PySide6.QtQuickWidgets,PySide6.QtNetwork,PySide6.QtSql,PySide6.QtPrintSupport,PySide6.QtDBus,PySide6.QtHelp,PySide6.QtConcurrent,PySide6.QtOpenGL,PySide6.QtSvg,PySide6.Shiboken6,sqlite3,email,http,xml,tkinter,distutils"
set "CMD=!CMD! --noinclude-unittest-mode=nofollow"
set "CMD=!CMD! --noinclude-pydoc-mode=nofollow"
set "CMD=!CMD! --noinclude-setuptools-mode=nofollow"
set "CMD=!CMD! --noinclude-pytest-mode=nofollow"


REM Include metadata for AV safety and professional look
set "CMD=!CMD! --company-name="%COMPANY_NAME%""
set "CMD=!CMD! --product-name="%PRODUCT_NAME%""
set "CMD=!CMD! --file-version=%FILE_VERSION%"
set "CMD=!CMD! --product-version=%PROD_VERSION%"
set "CMD=!CMD! --file-description="%FILE_DESC%""
set "CMD=!CMD! --copyright="%COPYRIGHT%""

REM Advanced size optimizations
set "CMD=!CMD! --lto=yes"
set "CMD=!CMD! --prefer-source-code"
set "CMD=!CMD! --include-windows-runtime-dlls=no"

REM Add the script to the command
set "CMD=!CMD! %SCRIPT%"

REM ============================
REM  Run the build
REM ============================

echo.
echo Running:
echo !CMD!
echo.
for /f "tokens=*" %%A in ('powershell -NoProfile -Command "(Get-Date).Ticks"') do set "TICKS_START=%%A"
for /f "tokens=*" %%A in ('powershell -NoProfile -Command "Get-Date -Format 'HH:mm:ss'"') do set "STR_START=%%A"
echo Build started at !STR_START!
echo.
call !CMD!
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)
for /f "tokens=*" %%A in ('powershell -NoProfile -Command "(Get-Date).Ticks"') do set "TICKS_END=%%A"
for /f "tokens=*" %%A in ('powershell -NoProfile -Command "$ts = New-Object TimeSpan([long]!TICKS_END! - [long]!TICKS_START!); $ts.ToString('hh\:mm\:ss')"') do set "DURATION=%%A"
echo Build finished.

REM ==================================
REM Post-build pruning (aggressive)
REM Removes all unnecessary bloat for
REM a minimal terminal emulator
REM ==================================
REM Determine actual dist folder. Nuitka sometimes uses the SCRIPT name.
set "SOURCE=DO_NOT_SYNC\build\%EXE_NAME%.dist"
if not exist "%SOURCE%" (
  for /f "delims=" %%D in ('dir "DO_NOT_SYNC\build\*.dist" /b 2^>nul') do (
    set "SOURCE=DO_NOT_SYNC\build\%%D"
    goto :found_dist
  )
  echo Dist folder not found: DO_NOT_SYNC\build\*.dist
  exit /b 1
)
:found_dist
echo Using dist folder: %SOURCE%

echo Measuring original size...
for /f "tokens=*" %%A in ('powershell -NoProfile -Command "$s=(Get-ChildItem -Path '!SOURCE!' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB; [math]::round($s, 2).ToString([System.Globalization.CultureInfo]::InvariantCulture)"') do set "SRC_SIZE=%%A"
echo Original build size: !SRC_SIZE! MB

if /i "%DO_PRUNE%"=="yes" (
    echo Starting post-build pruning...
    set "TARGET=DO_NOT_SYNC\build\pruned.dist"
    
    REM Extra safety check for pruning target
    if "!TARGET!"=="" ( echo ERROR: Prune TARGET is empty. & pause & exit /b 1 )
    if "!TARGET!"=="!SOURCE!" ( echo ERROR: Prune TARGET cannot be the same as SOURCE. & pause & exit /b 1 )
    
    echo Creating copy from !SOURCE! to !TARGET!...
    if exist "!TARGET!" rmdir /s /q "!TARGET!"
    
    REM Prefer robocopy (faster and reliable).
    where robocopy >nul 2>&1
    if !errorlevel!==0 (
        mkdir "!TARGET!" >nul 2>&1
        robocopy "!SOURCE!" "!TARGET!" /MIR /NFL /NDL /NJH /NJS
        if errorlevel 8 (
            powershell -NoProfile -Command "Copy-Item -Path '!SOURCE!' -Destination '!TARGET!' -Recurse -Force" >nul 2>&1
        )
    ) else (
        powershell -NoProfile -Command "Copy-Item -Path '!SOURCE!' -Destination '!TARGET!' -Recurse -Force" >nul 2>&1
    )

    echo Pruning !TARGET!...

    REM Remove unnecessary directories
    set "DIRS_TO_REMOVE=PySide6\qml PySide6\translations PySide6\plugins\imageformats PySide6\plugins\networkinformation PySide6\plugins\printsupport PySide6\plugins\sqldrivers PySide6\plugins\tls PySide6\plugins\bearer PySide6\plugins\generic PySide6\plugins\iconengines PySide6\plugins\platformthemes PySide6\plugins\styles __pycache__ tcl tk"
    for %%D in (%DIRS_TO_REMOVE%) do (
        if exist "!TARGET!\%%D" rmdir /s /q "!TARGET!\%%D" >nul 2>&1
    )

    REM Remove unnecessary file types
    echo Removing unnecessary file types...
    for %%F in (*.pyc *.pyo *.pdb *_d.dll *.lib *.a *.orig *.bak) do (
        del /s /q "!TARGET!\%%F" >nul 2>&1
    )

    REM Remove unused libraries using PowerShell for better accuracy
    echo Removing unused libraries using PowerShell...
    set "UNUSED_MODS=DBus Help Network OpenGL PrintSupport Qml Quick Sql Svg WebEngine Location Positioning Charts DataVisualization Multimedia Nfc Pdf RemoteObjects Sensors Serial Spatial StateMachine TextToSpeech VirtualKeyboard WebChannel WebSockets Xml libcrypto libssl unittest pydoc sqlite3 email http xml tkinter distutils _tkinter _sqlite3 _hashlib _ssl"
    for %%M in (%UNUSED_MODS%) do (
        powershell -NoProfile -Command "Get-ChildItem -Path '!TARGET!' -Filter '*%%M*' -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force -Recurse"
    )

    REM Cleanup extra shiboken files
    for %%S in (include CMake stubs) do (
        if exist "!TARGET!\shiboken6\%%S" rmdir /s /q "!TARGET!\shiboken6\%%S" >nul 2>&1
    )

    REM Remove non-essential platform DLLs
    set "UNUSED_PLUGS=canvas devtools geometry haptics imageformats networkinformation opengl printsupport renderers sceneparsers sensors sqldrivers tls virtualkeyboard"
    for %%P in (%UNUSED_PLUGS%) do (
        if exist "!TARGET!\PySide6\plugins\%%P" rmdir /s /q "!TARGET!\PySide6\plugins\%%P" >nul 2>&1
    )

    echo Calculating pruned size...
    for /f "tokens=*" %%A in ('powershell -NoProfile -Command "$s=(Get-ChildItem -Path '!TARGET!' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB; [math]::round($s, 2).ToString([System.Globalization.CultureInfo]::InvariantCulture)"') do set "TGT_SIZE=%%A"
    for /f "tokens=*" %%A in ('powershell -NoProfile -Command "$d = [double]'!SRC_SIZE!' - [double]'!TGT_SIZE!'; [math]::round($d, 2).ToString([System.Globalization.CultureInfo]::InvariantCulture)"') do set "SAVED_MB=%%A"
    for /f "tokens=*" %%A in ('powershell -NoProfile -Command "$src = [double]'!SRC_SIZE!'; if ($src -gt 0) { [math]::round(([double]'!SAVED_MB!' * 100) / $src, 1).ToString([System.Globalization.CultureInfo]::InvariantCulture) } else { '0' }"') do set "SAVED_PCT=%%A"

    echo.
    echo ===========================================
    echo Original size: !SRC_SIZE! MB
    echo Pruned size:   !TGT_SIZE! MB
    echo Saved:         !SAVED_MB! MB (~!SAVED_PCT!%%^)
    echo ===========================================
    echo.
    echo Pruned dist: !TARGET!
) else (
    echo Pruning is disabled. Skipping post-build cleanup.
)

echo.
echo Compilation Duration: !DURATION!
echo.

endlocal
