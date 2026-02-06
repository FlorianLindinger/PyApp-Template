<# :
:: =================================================
:: Usage: 
::  create_shortcut.bat "<name>" "<target>" "<target-args>" "<working-dir>" "<icon-path>" "<description>" "<appid>"
:: =================================================

@echo off
setlocal enabledelayedexpansion

:: get call arguments
set "NAME=%~1"
set "TARGET=%~2"
set "ARGS=%~3"
set "WDIR=%~4"
set "ICON=%~5"
set "DESC=%~6"
set "APPID=%~7"

:: replace "" with " in ARGS
if defined ARGS set "ARGS=%ARGS:""="%"

:: if no args given, try to find unique targets in current directory
if "%~1"=="" (
    REM Count total target files (.bat, .exe, .py)
    for /f %%A in ('dir /b /a-d *.bat *.exe *.py 2^>nul ^| findstr /v /i "%~nx0" ^| find /v /c ""') do set "totalCount=%%A"

    REM Count total icon files (.ico)
    for /f %%B in ('dir /b /a-d *.ico 2^>nul ^| find /v /c ""') do set "iconCount=%%B"

    REM Logic check for Targets (Must be exactly 1)
    if not "!totalCount!"=="1" (
        echo [ERROR] Found !totalCount! potential target files ^(.bat, .exe, .py^). 
        echo Total target count must be exactly 1 for auto-determination.
        goto :USAGE_ERROR
    )

    REM Logic check for Icons (Allows 0 or 1)
    if "!iconCount!" GTR "1" (
        echo [ERROR] Found !iconCount! icon files ^(.ico^). 
        echo Please provide only one .ico file for auto-determination or specify via arguments.
        goto :USAGE_ERROR
    )

    REM [SUCCESS] Capture the target filename
    for /f "delims=" %%F in ('dir /b /a-d *.bat *.exe *.py 2^>nul ^| findstr /v /i "%~nx0"') do (
        set "TARGET=%%F"
        set "NAME=%%~nF"
    )

    REM [SUCCESS] Capture the icon filename (if it exists)
    if "!iconCount!"=="1" (
        for /f "delims=" %%I in ('dir /b /a-d *.ico 2^>nul') do (
            set "ICON=%%I"
        )
        echo [SUCCESS] Auto-determined Icon:   !ICON!
    ) else (
        echo [INFO] No icon found. Using default system icon.
        set "ICON="
    )

    echo [SUCCESS] Auto-determined Target: !TARGET!
)

:: make paths absolute
call :set_abs_path "!NAME!" "NAME"
call :set_abs_path "!TARGET!" "TARGET"
call :set_abs_path "!WDIR!" "WDIR"

:: Only set absolute path for ICON if ICON is not empty
if not "!ICON!"=="" (
    call :set_abs_path "!ICON!" "ICON"
)

:: strip accidental .lnk from NAME
if /i "!NAME:~-4!"==".lnk" set "NAME=!NAME:~0,-4!"

:: make folder for shortcut if not existing
for %%D in ("!NAME!") do mkdir "%%~dpD" >nul 2>&1

:: add shortcut ending
set "LINK=!NAME!.lnk"

:: ========================================================
:: EXECUTION: Handover to Embedded PowerShell
:: ========================================================
:: We pass the variables via Environment Variables to the PS script
powershell -NoProfile -ExecutionPolicy Bypass -Command "iex (${%~f0} | out-string)"

:: test if shortcut was created and exit
if not exist "!LINK!" (
    echo [ERROR] Shortcut was not created.
    pause > nul
    exit /b 2
) else (
    echo [SUCCESS] Shortcut was created.
    exit /b 0
)

:: ====================
:: ==== Functions: ====
:: ====================

:set_abs_path
    if "%~2"=="" exit /b 1
    if "%~1"=="" (
        set "%~2=%CD%"
    ) else (
        set "%~2=%~f1"
    )
goto :EOF

:USAGE_ERROR
echo Usage: %~nx0 "name" "target" "args" "working_dir" "icon_path" "description" "appid"
pause > nul
exit /b 1
goto :eof

:: ========================================================
::  END BATCH / BEGIN POWERSHELL
:: ========================================================
: #>

# --- 1. Define C# Helper for AppUserModelID ---
$Source = @'
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

public static class AppIdHelper
{
    [DllImport("shell32.dll", SetLastError = true)]
    private static extern int SHGetPropertyStoreFromParsingName(
        [MarshalAs(UnmanagedType.LPWStr)] string pszPath,
        IntPtr pbc,
        uint flags,
        ref Guid riid,
        out IPropertyStore ppv);

    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DB3F999"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IPropertyStore
    {
        void GetCount(out uint cProps);
        void GetAt(uint iProp, out PropertyKey pkey);
        void GetValue(ref PropertyKey key, out PropVariant pv);
        void SetValue(ref PropertyKey key, ref PropVariant pv);
        void Commit();
    }

    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    private struct PropertyKey
    {
        public Guid fmtid;
        public uint pid;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct PropVariant
    {
        public ushort vt;
        public ushort wReserved1;
        public ushort wReserved2;
        public ushort wReserved3;
        public IntPtr unionMember;
        public IntPtr unionMember2;
    }

    public static void SetAppId(string shortcutPath, string appId)
    {
        Guid CLSID_IPropertyStore = new Guid("886D8EEB-8CF2-4446-8D02-CDBA1DB3F999");
        Guid PKEY_AppUserModel_ID_Fmt = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3");
        PropertyKey PKEY_AppUserModel_ID = new PropertyKey { fmtid = PKEY_AppUserModel_ID_Fmt, pid = 5 };

        IPropertyStore store;
        int hr = SHGetPropertyStoreFromParsingName(shortcutPath, IntPtr.Zero, 2, ref CLSID_IPropertyStore, out store); // 2 = GPS_READWRITE

        if (hr == 0)
        {
            PropVariant pv = new PropVariant();
            pv.vt = 31; // VT_LPWSTR
            pv.unionMember = Marshal.StringToCoTaskMemUni(appId);
            store.SetValue(ref PKEY_AppUserModel_ID, ref pv);
            store.Commit();
            Marshal.FreeCoTaskMem(pv.unionMember);
            Marshal.ReleaseComObject(store);
        }
    }
}
'@

# Silence the Add-Type output
try { Add-Type -TypeDefinition $Source -ErrorAction SilentlyContinue } catch {}

# --- 2. Create the Shortcut ---
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($env:LINK)

$lnk.TargetPath = $env:TARGET
$lnk.Arguments = $env:ARGS
$lnk.WorkingDirectory = $env:WDIR
$lnk.Description = $env:DESC

if (-not [string]::IsNullOrEmpty($env:ICON)) {
    $lnk.IconLocation = $env:ICON
}

$lnk.Save()

# --- 3. Apply AppID (If provided) ---
if (-not [string]::IsNullOrEmpty($env:APPID)) {
    # Brief pause to ensure file handle is released
    Start-Sleep -Milliseconds 200
    try {
        [AppIdHelper]::SetAppId($env:LINK, $env:APPID)
        Write-Host " + AppID applied: $env:APPID"
    } catch {
        Write-Host " ! Failed to set AppID" -ForegroundColor Red
    }
}