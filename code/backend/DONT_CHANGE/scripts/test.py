import base64
import ctypes
import json
import os
import re
import subprocess
import threading
import uuid
from ctypes import wintypes
from types import SimpleNamespace
from xml.sax.saxutils import escape as _xml_escape

ASCII_FONT_FILES = {
    "big money-ne": ("Big Money-ne", "big_money-ne.flf"),
    "standard": ("Standard", "standard.flf"),
    "coder mini": ("Coder Mini", "coder_mini.flf"),
    "future": ("Future", "future.tlf"),
    "future smooth": ("Future Smooth", "future_smooth.tlf"),
    "larry 3d 2": ("Larry 3D 2", "larry_3d_2.flf"),
}


_WIN_CONSTANTS = None
_NATIVE_TYPES = None
_WINDOWS_API = None
_WINDOW_STATES = {}


def _constants():
    global _WIN_CONSTANTS
    if _WIN_CONSTANTS is not None:
        return _WIN_CONSTANTS

    wm_user = 0x0400
    wm_app = 0x8000
    constants = SimpleNamespace(
        gwl_style=-16,
        gwl_exstyle=-20,
        ws_caption=0x00C00000,
        ws_thickframe=0x00040000,
        ws_minimizebox=0x00020000,
        ws_maximizebox=0x00010000,
        ws_ex_layered=0x00080000,
        ws_ex_topmost=0x00000008,
        lwa_alpha=0x00000002,
        sc_size=0xF000,
        sc_minimize=0xF020,
        sc_maximize=0xF030,
        sc_close=0xF060,
        mf_bycommand=0x00000000,
        mf_enabled=0x00000000,
        mf_grayed=0x00000001,
        mf_disabled=0x00000002,
        swp_nosize=0x0001,
        swp_nomove=0x0002,
        swp_nozorder=0x0004,
        swp_noactivate=0x0010,
        swp_framechanged=0x0020,
        hwnd_topmost=-1,
        hwnd_notopmost=-2,
        ga_root=2,
        wm_null=0x0000,
        wm_destroy=0x0002,
        wm_close=0x0010,
        wm_contextmenu=0x007B,
        wm_lbuttonup=0x0202,
        wm_lbuttondblclk=0x0203,
        wm_rbuttonup=0x0205,
        nin_select=wm_user,
        nin_keyselect=wm_user + 1,
        tray_callback=wm_app + 1,
        hide_target_message=wm_app + 2,
        nim_add=0x00000000,
        nim_delete=0x00000002,
        nim_setversion=0x00000004,
        nif_message=0x00000001,
        nif_icon=0x00000002,
        nif_tip=0x00000004,
        nif_guid=0x00000020,
        nif_showtip=0x00000080,
        notifyicon_version_4=4,
        event_system_minimizestart=0x0016,
        winevent_outofcontext=0x0000,
        sw_hide=0,
        sw_minimize=6,
        sw_restore=9,
        flashw_stop=0x00000000,
        flashw_caption=0x00000001,
        flashw_tray=0x00000002,
        flashw_all=0x00000003,
        flashw_timer=0x00000004,
        flashw_timernofg=0x0000000C,
        image_icon=1,
        lr_loadfromfile=0x0010,
        lr_defaultsize=0x0040,
        idi_application=32512,
        mf_string=0x0000,
        mf_separator=0x0800,
        tpm_rightbutton=0x0002,
        tpm_returncmd=0x0100,
        cmd_restore=1001,
        cmd_hide=1002,
        cmd_stop=1003,
        dwmwa_border_color=34,
        dwmwa_caption_color=35,
        dwmwa_text_color=36,
        dwmwa_color_default=0xFFFFFFFF,
        dwmwcp_default=0,
        dwmwcp_donotround=1,
        dwmwcp_round=2,
        dwmwcp_roundsmall=3,
    )
    _WIN_CONSTANTS = constants
    return constants


def _native_types():
    global _NATIVE_TYPES
    if _NATIVE_TYPES is not None:
        return _NATIVE_TYPES

    lresult = ctypes.c_ssize_t
    wparam = ctypes.c_size_t
    lparam = ctypes.c_ssize_t
    wndproc = ctypes.WINFUNCTYPE(lresult, wintypes.HWND, wintypes.UINT, wparam, lparam)
    wineventproc = ctypes.WINFUNCTYPE(
        None,
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.HWND,
        wintypes.LONG,
        wintypes.LONG,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    enum_windows_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    class WNDCLASSEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("style", wintypes.UINT),
            ("lpfnWndProc", wndproc),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HANDLE),
            ("hIcon", wintypes.HANDLE),
            ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HANDLE),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
            ("hIconSm", wintypes.HANDLE),
        ]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", wintypes.HANDLE),
            ("szTip", wintypes.WCHAR * 128),
            ("dwState", wintypes.DWORD),
            ("dwStateMask", wintypes.DWORD),
            ("szInfo", wintypes.WCHAR * 256),
            ("uVersion", wintypes.UINT),
            ("szInfoTitle", wintypes.WCHAR * 64),
            ("dwInfoFlags", wintypes.DWORD),
            ("guidItem", GUID),
            ("hBalloonIcon", wintypes.HANDLE),
        ]

    class FLASHWINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("hwnd", wintypes.HWND),
            ("dwFlags", wintypes.DWORD),
            ("uCount", wintypes.UINT),
            ("dwTimeout", wintypes.DWORD),
        ]

    types = SimpleNamespace(
        lresult=lresult,
        wparam=wparam,
        lparam=lparam,
        wndproc=wndproc,
        wineventproc=wineventproc,
        enum_windows_proc=enum_windows_proc,
        flashwinfo=FLASHWINFO,
        wndclassex=WNDCLASSEXW,
        notifyicondata=NOTIFYICONDATAW,
    )
    _NATIVE_TYPES = types
    return types


def _windows_api():
    global _WINDOWS_API
    if _WINDOWS_API is not None:
        return _WINDOWS_API

    types = _native_types()
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
    long_ptr = ctypes.c_ssize_t

    kernel32.GetConsoleWindow.argtypes = []
    kernel32.GetConsoleWindow.restype = wintypes.HWND
    kernel32.GetConsoleTitleW.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
    kernel32.GetConsoleTitleW.restype = wintypes.DWORD
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HANDLE

    user32.AppendMenuW.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
    user32.AppendMenuW.restype = wintypes.BOOL
    user32.CreatePopupMenu.argtypes = []
    user32.CreatePopupMenu.restype = wintypes.HANDLE
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.c_void_p,
    ]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, types.wparam, types.lparam]
    user32.DefWindowProcW.restype = types.lresult
    user32.DestroyIcon.argtypes = [wintypes.HANDLE]
    user32.DestroyIcon.restype = wintypes.BOOL
    user32.DestroyMenu.argtypes = [wintypes.HANDLE]
    user32.DestroyMenu.restype = wintypes.BOOL
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.DestroyWindow.restype = wintypes.BOOL
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.restype = types.lresult
    user32.DrawMenuBar.argtypes = [wintypes.HWND]
    user32.DrawMenuBar.restype = wintypes.BOOL
    user32.EnableMenuItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
    user32.EnableMenuItem.restype = wintypes.UINT
    user32.EnumWindows.argtypes = [types.enum_windows_proc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.FlashWindowEx.argtypes = [ctypes.POINTER(types.flashwinfo)]
    user32.FlashWindowEx.restype = wintypes.BOOL
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = ctypes.c_int
    user32.GetSystemMenu.argtypes = [wintypes.HWND, wintypes.BOOL]
    user32.GetSystemMenu.restype = wintypes.HMENU
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.LoadIconW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR]
    user32.LoadIconW.restype = wintypes.HANDLE
    user32.LoadImageW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCWSTR,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.LoadImageW.restype = wintypes.HANDLE
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, types.wparam, types.lparam]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.PostQuitMessage.argtypes = [ctypes.c_int]
    user32.PostQuitMessage.restype = None
    user32.RegisterClassExW.argtypes = [ctypes.POINTER(types.wndclassex)]
    user32.RegisterClassExW.restype = wintypes.WORD
    user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterWindowMessageW.restype = wintypes.UINT
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.SetLayeredWindowAttributes.argtypes = [
        wintypes.HWND,
        wintypes.COLORREF,
        ctypes.c_ubyte,
        wintypes.DWORD,
    ]
    user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
    user32.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HRGN, wintypes.BOOL]
    user32.SetWindowRgn.restype = ctypes.c_int
    user32.SetWinEventHook.argtypes = [
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
        types.wineventproc,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    user32.SetWinEventHook.restype = wintypes.HANDLE
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.TrackPopupMenu.argtypes = [
        wintypes.HANDLE,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        ctypes.c_void_p,
    ]
    user32.TrackPopupMenu.restype = wintypes.UINT
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.TranslateMessage.restype = wintypes.BOOL
    user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
    user32.UnhookWinEvent.restype = wintypes.BOOL
    user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE]
    user32.UnregisterClassW.restype = wintypes.BOOL

    shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(types.notifyicondata)]
    shell32.Shell_NotifyIconW.restype = wintypes.BOOL

    gdi32.CreateEllipticRgn.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    gdi32.CreateEllipticRgn.restype = wintypes.HRGN
    gdi32.CreateRectRgn.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    gdi32.CreateRectRgn.restype = wintypes.HRGN
    gdi32.CreateRoundRectRgn.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
    ]
    gdi32.CreateRoundRectRgn.restype = wintypes.HRGN
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL

    dwmapi.DwmSetWindowAttribute.argtypes = [
        wintypes.HWND,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long

    if ctypes.sizeof(ctypes.c_void_p) == 8:
        get_window_long = user32.GetWindowLongPtrW
        set_window_long = user32.SetWindowLongPtrW
    else:
        get_window_long = user32.GetWindowLongW
        set_window_long = user32.SetWindowLongW

    get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
    get_window_long.restype = long_ptr
    set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, long_ptr]
    set_window_long.restype = long_ptr

    api = SimpleNamespace(
        user32=user32,
        kernel32=kernel32,
        shell32=shell32,
        gdi32=gdi32,
        dwmapi=dwmapi,
        get_window_long=get_window_long,
        set_window_long=set_window_long,
    )
    _WINDOWS_API = api
    return api


def _window_states():
    return _WINDOW_STATES


def _raise_last_error(operation: str) -> None:
    error = ctypes.get_last_error()
    if error:
        raise ctypes.WinError(error)
    raise RuntimeError(f"{operation} failed.")


def _integer_resource(value: int) -> wintypes.LPCWSTR:
    return ctypes.cast(ctypes.c_void_p(value), wintypes.LPCWSTR)


def _tray_icon_guid() -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, "pyapp-template/native-minimize-to-tray")


def _set_notify_icon_guid(notify_icon_data: object, guid: uuid.UUID) -> None:
    notify_icon_data.guidItem.Data1 = guid.time_low
    notify_icon_data.guidItem.Data2 = guid.time_mid
    notify_icon_data.guidItem.Data3 = guid.time_hi_version
    for index, value in enumerate(guid.bytes[8:]):
        notify_icon_data.guidItem.Data4[index] = value


def _load_icon_from_file(icon_path: str) -> int:
    path = os.path.abspath(os.fspath(icon_path))
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    api = _windows_api()
    constants = _constants()
    icon = api.user32.LoadImageW(
        None,
        path,
        constants.image_icon,
        0,
        0,
        constants.lr_loadfromfile | constants.lr_defaultsize,
    )
    if not icon:
        raise ctypes.WinError(ctypes.get_last_error())
    return int(icon)


def _default_notification_settings():
    return SimpleNamespace(
        title="Python notification",
        message="Notification from test.py",
        app_id="",
        app_name="",
        duration="short",
        scenario="default",
        silent=False,
        sound="default",
        attribution="",
        logo="",
        hero="",
    )


_TOAST_SOUND_ALIASES = {
    "default": "",
    "mail": "ms-winsoundevent:Notification.Mail",
    "sms": "ms-winsoundevent:Notification.SMS",
    "reminder": "ms-winsoundevent:Notification.Reminder",
    "alarm": "ms-winsoundevent:Notification.Looping.Alarm",
    "call": "ms-winsoundevent:Notification.Looping.Call",
}


def _validate_windows_notification_settings(settings) -> None:
    settings.duration = getattr(settings, "duration", "short")
    settings.scenario = getattr(settings, "scenario", "default")
    settings.silent = bool(getattr(settings, "silent", False))
    settings.app_id = str(getattr(settings, "app_id", "") or "")
    settings.app_name = str(getattr(settings, "app_name", "") or "")
    settings.sound = str(getattr(settings, "sound", "default") or "default").lower().replace("-", "_")
    settings.attribution = str(getattr(settings, "attribution", "") or "")
    settings.logo = str(getattr(settings, "logo", "") or "")
    settings.hero = str(getattr(settings, "hero", "") or "")

    if settings.duration not in {"short", "long"}:
        raise ValueError("Toast duration must be short or long.")
    if settings.scenario not in {"default", "alarm", "reminder", "incomingCall"}:
        raise ValueError("Toast scenario must be default, alarm, reminder, or incomingCall.")
    if settings.sound not in _TOAST_SOUND_ALIASES:
        available = ", ".join(sorted(_TOAST_SOUND_ALIASES))
        raise ValueError(f"Toast sound must be one of: {available}.")


def _read_hkcu_dword(subkey: str, name: str) -> int | None:
    try:
        import winreg
    except ImportError:
        return None

    view_flags = [
        winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0),
        winreg.KEY_READ,
        winreg.KEY_READ | getattr(winreg, "KEY_WOW64_32KEY", 0),
    ]
    seen_flags: set[int] = set()
    for access in view_flags:
        if access in seen_flags:
            continue
        seen_flags.add(access)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, access) as key:
                value, value_type = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            continue
        except OSError:
            continue

        if value_type == winreg.REG_DWORD:
            return int(value)

    return None


def _windows_toast_block_reason(app_id: str | None = None) -> str | None:
    toast_enabled = _read_hkcu_dword(
        r"Software\Microsoft\Windows\CurrentVersion\PushNotifications",
        "ToastEnabled",
    )
    if toast_enabled == 0:
        return "Windows notifications are disabled globally."

    app_id = str(app_id or "").strip()
    if not app_id:
        return None

    app_enabled = _read_hkcu_dword(
        rf"Software\Microsoft\Windows\CurrentVersion\Notifications\Settings\{app_id}",
        "Enabled",
    )
    if app_enabled == 0:
        return f"Windows notifications are disabled for app id {app_id!r}."

    return None


def get_windows_notification_disabled_reason(app_id: str | None = None) -> str | None:
    """Return why Windows toast notifications are blocked, or None if they look enabled."""

    return _windows_toast_block_reason(app_id)


def are_windows_notifications_enabled(app_id: str | None = None) -> bool:
    """Return True when Windows toast notifications appear enabled for the app id."""

    return get_windows_notification_disabled_reason(app_id) is None


def _default_toast_app_id() -> str:
    return ""


def _run_encoded_powershell(script: str, *, timeout: int = 10) -> str:
    encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded_script,
        ],
        capture_output=True,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace") if completed.stderr else ""
        stdout = completed.stdout.decode("utf-8", errors="replace") if completed.stdout else ""
        detail = (stderr or stdout).strip()
        if detail:
            raise RuntimeError(f"PowerShell notification failed: {detail}")
        raise RuntimeError(f"PowerShell notification failed with exit code {completed.returncode}.")
    return completed.stdout.decode("utf-8", errors="replace").strip() if completed.stdout else ""


def _sanitize_toast_identity_name(name: str) -> str:
    name = " ".join(str(name or "").split()).strip()
    if not name:
        return "Python notification"

    invalid_filename_chars = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid_filename_chars or ord(char) < 32 else char for char in name)
    return cleaned.strip(" .")[:80] or "Python notification"


def _toast_app_id_from_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9.]+", "-", name.lower()).strip("-.")
    normalized = re.sub(r"-+", "-", normalized) or "python-notification"
    return f"pyapp-template.toast.{normalized[:80]}"


def _toast_identity_shortcut_path(app_name: str) -> str:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set; cannot create a Windows toast identity.")

    return os.path.join(
        appdata,
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "PyApp Template",
        f"{_sanitize_toast_identity_name(app_name)}.lnk",
    )


def _create_toast_identity_shortcut(shortcut_path: str, app_name: str) -> None:
    icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon.ico")
    payload = {
        "shortcut_path": shortcut_path,
        "target_path": os.environ.get("ComSpec", r"C:\Windows\System32\cmd.exe"),
        "arguments": "/c exit",
        "working_directory": os.getcwd(),
        "description": f"{app_name} notification identity",
        "icon_path": icon_path if os.path.exists(icon_path) else "",
    }
    payload_base64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    script = f"""
$ErrorActionPreference = "Stop"
$payloadJson = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("{payload_base64}"))
$payload = $payloadJson | ConvertFrom-Json
$parent = Split-Path -Parent ([string]$payload.shortcut_path)
if (-not [System.IO.Directory]::Exists($parent)) {{
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
}}
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut([string]$payload.shortcut_path)
$shortcut.TargetPath = [string]$payload.target_path
$shortcut.Arguments = [string]$payload.arguments
$shortcut.WorkingDirectory = [string]$payload.working_directory
$shortcut.Description = [string]$payload.description
if (-not [string]::IsNullOrWhiteSpace([string]$payload.icon_path)) {{
    $shortcut.IconLocation = [string]$payload.icon_path
}}
$shortcut.Save()
"""
    _run_encoded_powershell(script)


def _set_shortcut_app_user_model_id(shortcut_path: str, app_id: str) -> None:
    hresult = ctypes.c_long
    vt_lpwstr = 31
    s_ok = 0
    s_false = 1
    rpc_e_changed_mode = 0x80010106
    gps_readwrite = 0x00000002

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    class PROPERTYKEY(ctypes.Structure):
        _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]

    class PROPVARIANT(ctypes.Structure):
        _fields_ = [
            ("vt", ctypes.c_ushort),
            ("wReserved1", ctypes.c_ushort),
            ("wReserved2", ctypes.c_ushort),
            ("wReserved3", ctypes.c_ushort),
            ("pwszVal", ctypes.c_wchar_p),
        ]

    class IPropertyStore(ctypes.Structure):
        pass

    property_store_ptr = ctypes.POINTER(IPropertyStore)

    class IPropertyStoreVtbl(ctypes.Structure):
        _fields_ = [
            (
                "QueryInterface",
                ctypes.WINFUNCTYPE(
                    hresult,
                    property_store_ptr,
                    ctypes.POINTER(GUID),
                    ctypes.POINTER(ctypes.c_void_p),
                ),
            ),
            ("AddRef", ctypes.WINFUNCTYPE(ctypes.c_ulong, property_store_ptr)),
            ("Release", ctypes.WINFUNCTYPE(ctypes.c_ulong, property_store_ptr)),
            ("GetCount", ctypes.WINFUNCTYPE(hresult, property_store_ptr, ctypes.POINTER(wintypes.DWORD))),
            (
                "GetAt",
                ctypes.WINFUNCTYPE(hresult, property_store_ptr, wintypes.DWORD, ctypes.POINTER(PROPERTYKEY)),
            ),
            (
                "GetValue",
                ctypes.WINFUNCTYPE(
                    hresult,
                    property_store_ptr,
                    ctypes.POINTER(PROPERTYKEY),
                    ctypes.POINTER(PROPVARIANT),
                ),
            ),
            (
                "SetValue",
                ctypes.WINFUNCTYPE(
                    hresult,
                    property_store_ptr,
                    ctypes.POINTER(PROPERTYKEY),
                    ctypes.POINTER(PROPVARIANT),
                ),
            ),
            ("Commit", ctypes.WINFUNCTYPE(hresult, property_store_ptr)),
        ]

    IPropertyStore._fields_ = [("lpVtbl", ctypes.POINTER(IPropertyStoreVtbl))]

    def make_guid(value: str) -> GUID:
        parsed = uuid.UUID(value)
        return GUID(
            parsed.time_low,
            parsed.time_mid,
            parsed.time_hi_version,
            (ctypes.c_ubyte * 8)(*parsed.bytes[8:]),
        )

    def check_hresult(hr: int, action: str) -> None:
        if hr < 0:
            raise OSError(f"{action} failed with HRESULT 0x{hr & 0xFFFFFFFF:08X}")

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)

    shell32.SHGetPropertyStoreFromParsingName.argtypes = [
        wintypes.LPCWSTR,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(GUID),
        ctypes.POINTER(property_store_ptr),
    ]
    shell32.SHGetPropertyStoreFromParsingName.restype = hresult

    ole32.CoInitialize.argtypes = [ctypes.c_void_p]
    ole32.CoInitialize.restype = hresult
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None

    iid_property_store = make_guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")
    pkey_app_user_model_id = PROPERTYKEY(make_guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5)
    prop_var = PROPVARIANT()
    prop_var.vt = vt_lpwstr
    prop_var.pwszVal = app_id

    coinitialize_result = ole32.CoInitialize(None)
    should_uninitialize = coinitialize_result in {s_ok, s_false}
    if coinitialize_result < 0 and (coinitialize_result & 0xFFFFFFFF) != rpc_e_changed_mode:
        raise OSError(f"CoInitialize failed with HRESULT 0x{coinitialize_result & 0xFFFFFFFF:08X}")

    try:
        property_store = property_store_ptr()
        hr = shell32.SHGetPropertyStoreFromParsingName(
            os.path.abspath(shortcut_path),
            None,
            gps_readwrite,
            ctypes.byref(iid_property_store),
            ctypes.byref(property_store),
        )
        check_hresult(hr, f"SHGetPropertyStoreFromParsingName for {shortcut_path!r}")
        try:
            hr = property_store.contents.lpVtbl.contents.SetValue(
                property_store,
                ctypes.byref(pkey_app_user_model_id),
                ctypes.byref(prop_var),
            )
            check_hresult(hr, "SetValue System.AppUserModel.ID")
            hr = property_store.contents.lpVtbl.contents.Commit(property_store)
            check_hresult(hr, "Commit System.AppUserModel.ID")
        finally:
            if property_store:
                property_store.contents.lpVtbl.contents.Release(property_store)
    finally:
        if should_uninitialize:
            ole32.CoUninitialize()


def _ensure_toast_identity_for_name(app_name: str) -> str:
    app_name = _sanitize_toast_identity_name(app_name)
    app_id = _toast_app_id_from_name(app_name)
    shortcut_path = _toast_identity_shortcut_path(app_name)
    if not os.path.exists(shortcut_path):
        _create_toast_identity_shortcut(shortcut_path, app_name)
    _set_shortcut_app_user_model_id(shortcut_path, app_id)
    return app_id


def _toast_image_source(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if "://" in value or value.startswith(("ms-appx:", "ms-appdata:")):
        return value

    path = os.path.abspath(os.path.expandvars(os.path.expanduser(value)))
    return "file:///" + path.replace("\\", "/")


def _modern_toast_xml(settings) -> str:
    xml_escape = lambda value: _xml_escape(value, {'"': "&quot;", "'": "&apos;"})
    toast_attributes = [f'duration="{settings.duration}"']
    if settings.scenario != "default":
        toast_attributes.append(f'scenario="{settings.scenario}"')

    logo = _toast_image_source(settings.logo)
    hero = _toast_image_source(settings.hero)
    toast_xml_lines = [
        f"<toast {' '.join(toast_attributes)}>",
        "  <visual>",
        '    <binding template="ToastGeneric">',
    ]
    if logo:
        toast_xml_lines.append(f'      <image placement="appLogoOverride" src="{xml_escape(logo)}" />')
    if hero:
        toast_xml_lines.append(f'      <image placement="hero" src="{xml_escape(hero)}" />')
    toast_xml_lines.extend(
        [
            f"      <text>{xml_escape(settings.title[:200])}</text>",
            f"      <text>{xml_escape(settings.message[:600])}</text>",
        ]
    )
    if settings.attribution:
        toast_xml_lines.append(f'      <text placement="attribution">{xml_escape(settings.attribution[:200])}</text>')
    toast_xml_lines.extend(["    </binding>", "  </visual>"])
    if settings.silent:
        toast_xml_lines.append('  <audio silent="true" />')
    elif _TOAST_SOUND_ALIASES[settings.sound]:
        toast_xml_lines.append(f'  <audio src="{_TOAST_SOUND_ALIASES[settings.sound]}" />')
    toast_xml_lines.append("</toast>")
    return "\n".join(toast_xml_lines)


def _show_winrt_toast(settings) -> None:
    payload = {
        "app_id": settings.app_id,
        "xml": _modern_toast_xml(settings),
    }
    payload_base64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")

    script = f"""
$ErrorActionPreference = "Stop"
$payloadJson = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("{payload_base64}"))
$payload = $payloadJson | ConvertFrom-Json
Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
$null = [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime]
$null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml([string]$payload.xml)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$resolvedAppId = [string]$payload.app_id
if ([string]::IsNullOrWhiteSpace($resolvedAppId)) {{
    $startApp = Get-StartApps | Where-Object {{ $_.Name -eq "Windows PowerShell" }} | Select-Object -First 1
    if ($null -eq $startApp) {{
        $startApp = Get-StartApps | Where-Object {{ $_.Name -like "*PowerShell*" }} | Select-Object -First 1
    }}
    if ($null -ne $startApp) {{
        $resolvedAppId = [string]$startApp.AppID
    }}
}}
if ([string]::IsNullOrWhiteSpace($resolvedAppId)) {{
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier()
}} else {{
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($resolvedAppId)
}}
$notifier.Show($toast)
Write-Output ("TOAST_APP_ID=" + $resolvedAppId)
"""
    stdout = _run_encoded_powershell(script)
    if stdout:
        print(stdout)


def show_modern_windows_notification(settings=None) -> None:
    """Show a Windows toast notification through the standard WinRT API."""

    if settings is None:
        settings = _default_notification_settings()

    _validate_windows_notification_settings(settings)
    if settings.app_name:
        settings.app_id = _ensure_toast_identity_for_name(settings.app_name)
    else:
        settings.app_id = str(settings.app_id or "").strip()

    toast_block_reason = get_windows_notification_disabled_reason(settings.app_id)
    if toast_block_reason is not None:
        print(f"Windows toast suppressed: {toast_block_reason}")
        return

    _show_winrt_toast(settings)


def get_terminal_window():
    """Return the visible host window that owns the current terminal session."""

    api = _windows_api()
    constants = _constants()
    native_types = _native_types()
    user32 = api.user32
    kernel32 = api.kernel32

    def get_console_title() -> str:
        buffer = ctypes.create_unicode_buffer(1024)
        length = kernel32.GetConsoleTitleW(buffer, len(buffer))
        if length == 0:
            return ""
        return buffer.value

    def get_window_class(hwnd: int) -> str:
        if not hwnd:
            return ""
        buffer = ctypes.create_unicode_buffer(256)
        if not user32.GetClassNameW(hwnd, buffer, len(buffer)):
            return ""
        return buffer.value

    def get_window_title(hwnd: int) -> str:
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value

    def root_window(hwnd: int) -> int:
        if not hwnd:
            return 0
        return int(user32.GetAncestor(hwnd, constants.ga_root) or hwnd)

    def window_info(hwnd: int, source: str):
        hwnd = root_window(hwnd)
        if not hwnd or not user32.IsWindow(hwnd):
            return None
        return SimpleNamespace(
            hwnd=int(hwnd),
            class_name=get_window_class(hwnd),
            title=get_window_title(hwnd),
            source=source,
        )

    def is_windows_terminal(info) -> bool:
        return "CASCADIA" in info.class_name.upper()

    def is_conhost(info) -> bool:
        return info.class_name == "ConsoleWindowClass"

    def title_matches(window_title: str, console_title: str) -> bool:
        if not console_title:
            return False
        return window_title == console_title or console_title in window_title

    def visible_top_level_windows() -> list:
        windows = []

        @native_types.enum_windows_proc
        def callback(hwnd: int, _lparam: int) -> bool:
            if user32.IsWindowVisible(hwnd):
                info = window_info(int(hwnd), "enum")
                if info is not None:
                    windows.append(info)
            return True

        if not user32.EnumWindows(callback, 0):
            _raise_last_error("EnumWindows")

        return windows

    def candidate_windows(console_title: str) -> list:
        candidates = []
        seen: set[int] = set()

        def add(hwnd: int, source: str) -> None:
            info = window_info(hwnd, source)
            if info is None or info.hwnd in seen:
                return
            seen.add(info.hwnd)
            candidates.append(info)

        add(int(user32.GetForegroundWindow() or 0), "foreground")
        add(int(kernel32.GetConsoleWindow() or 0), "console")

        if console_title:
            add(int(user32.FindWindowW("ConsoleWindowClass", console_title) or 0), "console-title-class")
            add(int(user32.FindWindowW(None, console_title) or 0), "window-title")

        for info in visible_top_level_windows():
            if is_windows_terminal(info) and title_matches(info.title, console_title):
                add(info.hwnd, "windows-terminal-title")

        return candidates

    def format_window_infos(windows: list) -> str:
        if not windows:
            return "none"
        return "\n".join(
            f"- hwnd=0x{info.hwnd:016X}, class={info.class_name!r}, title={info.title!r}, source={info.source}"
            for info in windows
        )

    def as_terminal_window(info, host: str):
        return SimpleNamespace(
            hwnd=info.hwnd,
            host=host,
            class_name=info.class_name,
            title=info.title,
            source=info.source,
        )

    console_title = get_console_title()
    candidates = candidate_windows(console_title)

    if os.environ.get("WT_SESSION"):
        for info in candidates:
            if is_windows_terminal(info) and title_matches(info.title, console_title):
                return as_terminal_window(info, "windows-terminal")

        wt_windows = [info for info in visible_top_level_windows() if is_windows_terminal(info)]
        matching_wt_windows = [info for info in wt_windows if title_matches(info.title, console_title)]

        if len(matching_wt_windows) == 1:
            return as_terminal_window(matching_wt_windows[0], "windows-terminal")

        if len(wt_windows) == 1:
            return as_terminal_window(wt_windows[0], "windows-terminal")

        raise RuntimeError(
            "Windows Terminal was detected via WT_SESSION, but the outer wt.exe "
            "window could not be identified safely.\n"
            f"Console title: {console_title!r}\n"
            f"Candidates:\n{format_window_infos(candidates)}\n"
            f"Visible Windows Terminal windows:\n{format_window_infos(wt_windows)}"
        )

    for info in candidates:
        if is_conhost(info):
            return as_terminal_window(info, "conhost")

    console_hwnd = int(kernel32.GetConsoleWindow() or 0)
    if console_hwnd:
        info = window_info(console_hwnd, "console")
        if info is not None:
            return as_terminal_window(info, "conhost")

    raise RuntimeError(
        "The process does not appear to have a visible terminal window.\n"
        f"Console title: {console_title!r}\n"
        f"Candidates:\n{format_window_infos(candidates)}"
    )


def _get_window_long(hwnd: int, index: int) -> int:
    api = _windows_api()
    ctypes.set_last_error(0)
    value = api.get_window_long(hwnd, index)
    error = ctypes.get_last_error()
    if value == 0 and error:
        raise ctypes.WinError(error)
    return int(value)


def _set_window_long(hwnd: int, index: int, value: int) -> None:
    api = _windows_api()
    ctypes.set_last_error(0)
    previous = api.set_window_long(hwnd, index, value)
    error = ctypes.get_last_error()
    if previous == 0 and error:
        raise ctypes.WinError(error)


def _get_state(hwnd: int):
    constants = _constants()
    states = _window_states()
    state = states.get(hwnd)
    if state is None:
        original_ex_style = _get_window_long(hwnd, constants.gwl_exstyle)
        state = SimpleNamespace(
            original_style=_get_window_long(hwnd, constants.gwl_style),
            original_ex_style=original_ex_style,
            original_topmost=bool(original_ex_style & constants.ws_ex_topmost),
            title_bar_hidden=False,
            minimize_disabled=False,
            maximize_disabled=False,
            resize_disabled=False,
            close_disabled=False,
            opacity_percent=None,
            frame_changed=False,
        )
        states[hwnd] = state
    return state


def _resolve_window(window=None):
    return window if window is not None else get_terminal_window()


def _set_menu_command_enabled(hwnd: int, command: int, enabled: bool) -> None:
    api = _windows_api()
    constants = _constants()

    menu = api.user32.GetSystemMenu(hwnd, False)
    if not menu:
        return

    flags = constants.mf_bycommand
    if enabled:
        flags |= constants.mf_enabled
    else:
        flags |= constants.mf_disabled | constants.mf_grayed

    api.user32.EnableMenuItem(menu, command, flags)


def _refresh_frame(hwnd: int) -> None:
    api = _windows_api()
    constants = _constants()
    flags = (
        constants.swp_nomove
        | constants.swp_nosize
        | constants.swp_nozorder
        | constants.swp_noactivate
        | constants.swp_framechanged
    )

    if not api.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, flags):
        _raise_last_error("SetWindowPos")
    api.user32.DrawMenuBar(hwnd)


def _apply_state(hwnd: int) -> None:
    constants = _constants()
    state = _get_state(hwnd)
    style = state.original_style

    if state.title_bar_hidden:
        style &= ~constants.ws_caption
    if state.minimize_disabled:
        style &= ~constants.ws_minimizebox
    if state.maximize_disabled:
        style &= ~constants.ws_maximizebox
    if state.resize_disabled:
        style &= ~constants.ws_thickframe

    _set_window_long(hwnd, constants.gwl_style, style)

    _set_menu_command_enabled(hwnd, constants.sc_minimize, not state.minimize_disabled)
    _set_menu_command_enabled(hwnd, constants.sc_maximize, not state.maximize_disabled)
    _set_menu_command_enabled(hwnd, constants.sc_size, not state.resize_disabled)
    _set_menu_command_enabled(hwnd, constants.sc_close, not state.close_disabled)
    _refresh_frame(hwnd)


def set_always_on_top(enabled: bool = True, window=None) -> str:
    terminal_window = _resolve_window(window)
    constants = _constants()
    api = _windows_api()
    _get_state(terminal_window.hwnd)

    insert_after = constants.hwnd_topmost if enabled else constants.hwnd_notopmost
    flags = constants.swp_nomove | constants.swp_nosize | constants.swp_noactivate
    if not api.user32.SetWindowPos(terminal_window.hwnd, insert_after, 0, 0, 0, 0, flags):
        _raise_last_error("SetWindowPos")
    return terminal_window.host


def set_title_bar_hidden(hidden: bool = True, window=None) -> str:
    terminal_window = _resolve_window(window)
    state = _get_state(terminal_window.hwnd)
    state.title_bar_hidden = hidden
    _apply_state(terminal_window.hwnd)
    return terminal_window.host


def set_minimize_button_disabled(disabled: bool = True, window=None) -> str:
    terminal_window = _resolve_window(window)
    state = _get_state(terminal_window.hwnd)
    state.minimize_disabled = disabled
    _apply_state(terminal_window.hwnd)
    return terminal_window.host


def set_maximize_button_disabled(disabled: bool = True, window=None) -> str:
    terminal_window = _resolve_window(window)
    state = _get_state(terminal_window.hwnd)
    state.maximize_disabled = disabled
    _apply_state(terminal_window.hwnd)
    return terminal_window.host


def set_resize_disabled(disabled: bool = True, window=None) -> str:
    terminal_window = _resolve_window(window)
    state = _get_state(terminal_window.hwnd)
    state.resize_disabled = disabled
    _apply_state(terminal_window.hwnd)
    return terminal_window.host


def set_x_button_disabled(disabled: bool = True, window=None) -> str:
    terminal_window = _resolve_window(window)
    state = _get_state(terminal_window.hwnd)
    state.close_disabled = disabled
    _apply_state(terminal_window.hwnd)
    return terminal_window.host


def set_window_opacity(percent: int, window=None) -> str:
    terminal_window = _resolve_window(window)
    constants = _constants()
    api = _windows_api()
    state = _get_state(terminal_window.hwnd)

    alpha = round(percent * 255 / 100)
    ex_style = _get_window_long(terminal_window.hwnd, constants.gwl_exstyle)
    if not ex_style & constants.ws_ex_layered:
        _set_window_long(terminal_window.hwnd, constants.gwl_exstyle, ex_style | constants.ws_ex_layered)

    if not api.user32.SetLayeredWindowAttributes(terminal_window.hwnd, 0, alpha, constants.lwa_alpha):
        _raise_last_error("SetLayeredWindowAttributes")

    state.opacity_percent = percent
    return terminal_window.host


def restore_and_foreground_window(window=None) -> str:
    terminal_window = _resolve_window(window)
    api = _windows_api()
    constants = _constants()

    api.user32.ShowWindow(terminal_window.hwnd, constants.sw_restore)
    api.user32.BringWindowToTop(terminal_window.hwnd)
    api.user32.SetForegroundWindow(terminal_window.hwnd)
    return terminal_window.host


def flash_taskbar(
    window=None,
    *,
    count: int = 0,
    timeout_ms: int = 0,
    until_foreground: bool = True,
) -> str:
    terminal_window = _resolve_window(window)
    constants = _constants()
    types = _native_types()
    api = _windows_api()

    flags = constants.flashw_all
    if until_foreground:
        flags |= constants.flashw_timernofg
    elif count == 0:
        flags |= constants.flashw_timer

    info = types.flashwinfo()
    info.cbSize = ctypes.sizeof(types.flashwinfo)
    info.hwnd = terminal_window.hwnd
    info.dwFlags = flags
    info.uCount = count
    info.dwTimeout = timeout_ms

    if not api.user32.FlashWindowEx(ctypes.byref(info)):
        _raise_last_error("FlashWindowEx")

    return terminal_window.host


def _parse_colorref(value: str) -> int:
    normalized = value.strip().removeprefix("#").removeprefix("0x")
    if len(normalized) != 6:
        raise ValueError("Color must be #RRGGBB or RRGGBB.")

    red = int(normalized[0:2], 16)
    green = int(normalized[2:4], 16)
    blue = int(normalized[4:6], 16)
    return red | (green << 8) | (blue << 16)


def _set_dwm_int_attribute(hwnd: int, attribute: int, value: int) -> None:
    api = _windows_api()
    data = ctypes.c_int(value)
    result = api.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))
    if result < 0:
        raise OSError(f"DwmSetWindowAttribute failed with HRESULT 0x{result & 0xFFFFFFFF:08X}")


def set_frame_border_color(color: str, window=None) -> str:
    terminal_window = _resolve_window(window)
    constants = _constants()
    _get_state(terminal_window.hwnd).frame_changed = True
    _set_dwm_int_attribute(terminal_window.hwnd, constants.dwmwa_border_color, _parse_colorref(color))
    return terminal_window.host


def set_frame_caption_color(color: str, window=None) -> str:
    terminal_window = _resolve_window(window)
    constants = _constants()
    _get_state(terminal_window.hwnd).frame_changed = True
    _set_dwm_int_attribute(terminal_window.hwnd, constants.dwmwa_caption_color, _parse_colorref(color))
    return terminal_window.host


def set_frame_text_color(color: str, window=None) -> str:
    terminal_window = _resolve_window(window)
    constants = _constants()
    _get_state(terminal_window.hwnd).frame_changed = True
    _set_dwm_int_attribute(terminal_window.hwnd, constants.dwmwa_text_color, _parse_colorref(color))
    return terminal_window.host


def _load_figlet_font(font_name: str):
    # Normalize friendly font names such as "big_money-ne" and "Big Money-ne".
    normalized = " ".join(font_name.strip().lower().replace("_", " ").split())
    font_info = ASCII_FONT_FILES.get(normalized)
    if font_info is None:
        available = ", ".join(name for name, _filename in ASCII_FONT_FILES.values())
        raise ValueError(f"Unknown ASCII font {font_name!r}. Available fonts: {available}.")

    display_name, filename = font_info
    # Load from this script's local ascii_fonts directory.
    font_path = os.path.join(os.path.dirname(__file__), "ascii_fonts", filename)
    with open(font_path, encoding="utf-8") as font_file:
        lines = font_file.read().splitlines()
    if not lines:
        raise ValueError(f"ASCII font file is empty: {font_path}")

    header_parts = lines[0].split()
    signature = header_parts[0]
    if not (signature.startswith("flf2a") or signature.startswith("tlf2a")):
        raise ValueError(f"Unsupported ASCII font header in {font_path}: {signature!r}")
    if len(header_parts) < 6:
        raise ValueError(f"ASCII font header is incomplete in {font_path}.")

    hardblank = signature[-1]
    height = int(header_parts[1])
    comment_lines = int(header_parts[5])
    glyph_start = 1 + comment_lines
    glyphs: dict[str, tuple[str, ...]] = {}

    for offset, codepoint in enumerate(range(32, 127)):
        start = glyph_start + offset * height
        glyph_lines = lines[start : start + height]
        if len(glyph_lines) < height:
            raise ValueError(f"ASCII font {display_name} is missing glyph data for {chr(codepoint)!r}.")

        endmark = glyph_lines[-1][-1:] if glyph_lines[-1] else ""
        glyphs[chr(codepoint)] = tuple(line.rstrip(endmark) for line in glyph_lines)

    return SimpleNamespace(name=display_name, hardblank=hardblank, height=height, glyphs=glyphs)


def render_ascii_message(message: str, font_name: str = "Standard") -> str:
    """Render text with one of the local FIGlet-style ASCII fonts."""

    font = _load_figlet_font(font_name)
    fallback = font.glyphs.get("?", font.glyphs[" "])
    rendered_lines: list[str] = []

    for source_line in message.splitlines() or [""]:
        output_rows = ["" for _ in range(font.height)]
        for character in source_line:
            glyph = font.glyphs.get(character, fallback)
            for index, glyph_line in enumerate(glyph):
                output_rows[index] += glyph_line
        rendered_lines.extend(row.replace(font.hardblank, " ").rstrip() for row in output_rows)

    return "\n".join(rendered_lines)


def print_in_ASCII_font(message: str, font_name: str = "Standard") -> None:
    """Print a message using a local FIGlet-style ASCII font."""

    print(render_ascii_message(message, font_name))


def _parse_ascii_message_command(argument_text: str) -> tuple[str, str]:
    argument_text = argument_text.strip()
    if not argument_text:
        return "Standard", "Type Something"

    # Normalize user-entered font names without a separate one-use helper.
    normalized_argument = " ".join(argument_text.lower().replace("_", " ").split())
    for normalized_font, (display_name, _filename) in sorted(
        ASCII_FONT_FILES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if normalized_argument == normalized_font:
            return display_name, "Type Something"
        if normalized_argument.startswith(normalized_font + " "):
            font_prefix_length = len(display_name)
            return display_name, argument_text[font_prefix_length:].strip()

    first, separator, remainder = argument_text.partition("=")
    normalized_key = " ".join(first.lower().replace("_", " ").split())
    if separator and normalized_key in {"font", "ascii font"}:
        font_value, _separator, message = remainder.partition(" ")
        return font_value.strip(), message.strip() or "Type Something"

    return "Standard", argument_text


def apply_window_controls(
    *,
    always_on_top: bool = False,
    hide_title_bar: bool = False,
    disable_minimize_button: bool = False,
    disable_maximize_button: bool = False,
    disable_resize: bool = False,
    disable_x_button: bool = False,
    window=None,
):
    terminal_window = _resolve_window(window)
    state = _get_state(terminal_window.hwnd)
    state.title_bar_hidden = hide_title_bar
    state.minimize_disabled = disable_minimize_button
    state.maximize_disabled = disable_maximize_button
    state.resize_disabled = disable_resize
    state.close_disabled = disable_x_button

    _apply_state(terminal_window.hwnd)
    set_always_on_top(always_on_top, terminal_window)
    return terminal_window


class NativeMinimizeToTray:
    """Hidden message-window controller for hide-to-tray behavior."""

    def __init__(
        self,
        target_hwnd: int,
        *,
        tooltip: str = "Python program",
        icon_path: str | None = None,
        restore_on_stop: bool = True,
    ) -> None:
        api = _windows_api()
        if not api.user32.IsWindow(target_hwnd):
            raise ValueError("The target window handle is invalid.")

        self.target_hwnd = target_hwnd
        self.tooltip = tooltip[:127]
        self.icon_path = os.path.abspath(os.fspath(icon_path)) if icon_path is not None else None
        self.restore_on_stop = restore_on_stop

        self._window: int | None = None
        self._hook: int | None = None
        self._icon_handle: int | None = None
        self._owns_icon = False
        self._window_class_name = f"PythonNativeTray_{os.getpid()}_{id(self)}"
        self._ready = threading.Event()
        self._stopped = threading.Event()
        self._error: BaseException | None = None
        self._wndproc_callback = None
        self._event_callback = None
        self._nid = None
        self._taskbar_created = api.user32.RegisterWindowMessageW("TaskbarCreated")
        self._hidden_to_tray = False
        self._thread = threading.Thread(target=self._message_loop, name="NativeTrayController", daemon=True)

    def start(self) -> "NativeMinimizeToTray":
        self._thread.start()

        if not self._ready.wait(timeout=5):
            raise RuntimeError("Tray controller startup timed out.")

        if self._error is not None:
            raise RuntimeError("Could not start the tray controller.") from self._error

        return self

    def hide(self) -> None:
        api = _windows_api()
        constants = _constants()
        if api.user32.IsWindow(self.target_hwnd):
            self._add_tray_icon()
            self._hidden_to_tray = True
            api.user32.ShowWindow(self.target_hwnd, constants.sw_hide)

    def restore(self) -> None:
        api = _windows_api()
        constants = _constants()
        if api.user32.IsWindow(self.target_hwnd):
            api.user32.ShowWindow(self.target_hwnd, constants.sw_restore)
            api.user32.SetForegroundWindow(self.target_hwnd)
        self._hidden_to_tray = False
        self._remove_tray_icon()

    def toggle(self) -> None:
        api = _windows_api()
        if api.user32.IsWindowVisible(self.target_hwnd):
            self.hide()
        else:
            self.restore()

    def stop(self, *, restore: bool | None = None) -> None:
        api = _windows_api()
        constants = _constants()
        if restore is not None:
            self.restore_on_stop = restore

        if self._window and api.user32.IsWindow(self._window):
            api.user32.PostMessageW(self._window, constants.wm_close, 0, 0)

        if self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=3)

    def _load_icon(self) -> int:
        api = _windows_api()
        constants = _constants()
        if self.icon_path is not None:
            icon = _load_icon_from_file(self.icon_path)
            self._owns_icon = True
            return int(icon)

        icon = api.user32.LoadIconW(None, _integer_resource(constants.idi_application))
        if not icon:
            raise ctypes.WinError(ctypes.get_last_error())

        self._owns_icon = False
        return int(icon)

    def _add_tray_icon(self) -> None:
        assert self._window is not None
        assert self._icon_handle is not None

        if self._nid is not None:
            return

        api = _windows_api()
        constants = _constants()
        types = _native_types()
        nid = types.notifyicondata()
        nid.cbSize = ctypes.sizeof(types.notifyicondata)
        nid.hWnd = self._window
        nid.uID = 1
        nid.uFlags = (
            constants.nif_message | constants.nif_icon | constants.nif_tip | constants.nif_guid | constants.nif_showtip
        )
        nid.uCallbackMessage = constants.tray_callback
        nid.hIcon = self._icon_handle
        nid.szTip = self.tooltip
        _set_notify_icon_guid(nid, _tray_icon_guid())

        if not api.shell32.Shell_NotifyIconW(constants.nim_add, ctypes.byref(nid)):
            raise ctypes.WinError(ctypes.get_last_error())

        nid.uVersion = constants.notifyicon_version_4
        api.shell32.Shell_NotifyIconW(constants.nim_setversion, ctypes.byref(nid))
        self._nid = nid

    def _remove_tray_icon(self) -> None:
        if self._nid is not None:
            api = _windows_api()
            api.shell32.Shell_NotifyIconW(_constants().nim_delete, ctypes.byref(self._nid))
            self._nid = None

    def _show_menu(self) -> None:
        if self._window is None:
            return

        api = _windows_api()
        constants = _constants()
        menu = api.user32.CreatePopupMenu()
        if not menu:
            return

        try:
            api.user32.AppendMenuW(menu, constants.mf_string, constants.cmd_restore, "Restore")
            api.user32.AppendMenuW(menu, constants.mf_string, constants.cmd_hide, "Hide")
            api.user32.AppendMenuW(menu, constants.mf_separator, 0, None)
            api.user32.AppendMenuW(menu, constants.mf_string, constants.cmd_stop, "Stop tray controller")

            point = wintypes.POINT()
            api.user32.GetCursorPos(ctypes.byref(point))
            api.user32.SetForegroundWindow(self._window)
            command = api.user32.TrackPopupMenu(
                menu,
                constants.tpm_rightbutton | constants.tpm_returncmd,
                point.x,
                point.y,
                0,
                self._window,
                None,
            )

            if command == constants.cmd_restore:
                self.restore()
            elif command == constants.cmd_hide:
                self.hide()
            elif command == constants.cmd_stop:
                api.user32.PostMessageW(self._window, constants.wm_close, 0, 0)

            api.user32.PostMessageW(self._window, constants.wm_null, 0, 0)
        finally:
            api.user32.DestroyMenu(menu)

    def _window_proc(self, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        api = _windows_api()
        constants = _constants()

        if message == constants.tray_callback:
            event = int(lparam) & 0xFFFF
            if event in (
                constants.wm_lbuttonup,
                constants.wm_lbuttondblclk,
                constants.nin_select,
                constants.nin_keyselect,
            ):
                self.restore()
            elif event in (constants.wm_rbuttonup, constants.wm_contextmenu):
                self._show_menu()
            return 0

        if message == constants.hide_target_message:
            self.hide()
            return 0

        if message == self._taskbar_created:
            if self._hidden_to_tray:
                self._add_tray_icon()
            return 0

        if message == constants.wm_close:
            api.user32.DestroyWindow(hwnd)
            return 0

        if message == constants.wm_destroy:
            api.user32.PostQuitMessage(0)
            return 0

        return api.user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def _install_event_hook(self) -> None:
        assert self._window is not None

        api = _windows_api()
        constants = _constants()
        types = _native_types()
        process_id = wintypes.DWORD()
        api.user32.GetWindowThreadProcessId(self.target_hwnd, ctypes.byref(process_id))

        @types.wineventproc
        def event_callback(_hook, _event, event_hwnd, _object_id, _child_id, _event_thread, _event_time):
            try:
                if event_hwnd and int(event_hwnd) == self.target_hwnd:
                    api.user32.PostMessageW(self._window, constants.hide_target_message, 0, 0)
            except Exception:
                pass

        self._event_callback = event_callback
        hook = api.user32.SetWinEventHook(
            constants.event_system_minimizestart,
            constants.event_system_minimizestart,
            None,
            self._event_callback,
            process_id.value,
            0,
            constants.winevent_outofcontext,
        )
        if not hook:
            raise ctypes.WinError(ctypes.get_last_error())

        self._hook = int(hook)

    def _message_loop(self) -> None:
        api = _windows_api()
        constants = _constants()
        types = _native_types()
        instance = api.kernel32.GetModuleHandleW(None)
        class_registered = False

        try:

            @types.wndproc
            def window_callback(hwnd, message, wparam, lparam):
                try:
                    return self._window_proc(hwnd, message, wparam, lparam)
                except Exception:
                    return api.user32.DefWindowProcW(hwnd, message, wparam, lparam)

            self._wndproc_callback = window_callback

            window_class = types.wndclassex()
            window_class.cbSize = ctypes.sizeof(types.wndclassex)
            window_class.lpfnWndProc = self._wndproc_callback
            window_class.hInstance = instance
            window_class.lpszClassName = self._window_class_name

            if not api.user32.RegisterClassExW(ctypes.byref(window_class)):
                raise ctypes.WinError(ctypes.get_last_error())

            class_registered = True
            window = api.user32.CreateWindowExW(
                0,
                self._window_class_name,
                self._window_class_name,
                0,
                0,
                0,
                0,
                0,
                None,
                None,
                instance,
                None,
            )
            if not window:
                raise ctypes.WinError(ctypes.get_last_error())

            self._window = int(window)
            self._icon_handle = self._load_icon()
            self._install_event_hook()
            self._ready.set()

            message = wintypes.MSG()
            while True:
                result = api.user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == 0:
                    break
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())

                api.user32.TranslateMessage(ctypes.byref(message))
                api.user32.DispatchMessageW(ctypes.byref(message))

        except BaseException as error:
            self._error = error
            self._ready.set()
        finally:
            if self.restore_on_stop:
                self.restore()

            if self._hook:
                api.user32.UnhookWinEvent(self._hook)
                self._hook = None

            self._remove_tray_icon()

            if self._icon_handle and self._owns_icon:
                api.user32.DestroyIcon(self._icon_handle)

            if self._window and api.user32.IsWindow(self._window):
                api.user32.DestroyWindow(self._window)

            if class_registered:
                api.user32.UnregisterClassW(self._window_class_name, instance)

            self._stopped.set()


def enable_minimize_to_tray(
    *,
    tooltip: str = "Python program",
    icon_path: str | None = None,
    hwnd: int | None = None,
    window=None,
    restore_on_stop: bool = True,
) -> NativeMinimizeToTray:
    """Convert the terminal's minimize action into hide-to-tray."""

    if hwnd is None:
        hwnd = _resolve_window(window).hwnd

    return NativeMinimizeToTray(
        hwnd,
        tooltip=tooltip,
        icon_path=icon_path,
        restore_on_stop=restore_on_stop,
    ).start()


def _ensure_tray_controller(context) -> NativeMinimizeToTray:
    if context.tray_controller is None:
        context.tray_controller = enable_minimize_to_tray(
            tooltip=context.window.title,
            icon_path=context.tray_icon_path,
            window=context.window,
            restore_on_stop=True,
        )
    return context.tray_controller


def _parse_modern_toast_settings(
    argument_text: str,
    *,
    default_title: str,
):
    """Parse the REPL notify command into toast settings."""

    title = default_title or "Python notification"
    message = "Notification from test.py"
    app_id = ""
    app_name = ""
    duration = "short"
    scenario = "default"
    silent = False
    sound = "default"
    attribution = ""
    logo = ""
    hero = ""

    tokens = argument_text.split()
    remainder_start = 0
    for index, token in enumerate(tokens):
        normalized = token.lower().replace("-", "_")
        key, separator, value = normalized.partition("=")
        original_value = token.partition("=")[2] if separator else ""

        if separator and key in {"app_id", "appid", "aumid"}:
            app_id = original_value
        elif separator and key in {"app_name", "appname", "toast_name"}:
            app_name = original_value
        elif separator and key == "duration":
            duration = value
        elif separator and key == "scenario":
            scenario = "incomingCall" if value in {"incoming_call", "incomingcall"} else value
        elif separator and key == "sound":
            sound = "default" if value in {"", "default"} else value
            if value in {"none", "silent", "off", "false"}:
                silent = True
                sound = "default"
            else:
                silent = False
        elif separator and key == "attribution":
            attribution = original_value
        elif separator and key in {"logo", "image", "app_logo"}:
            logo = original_value
        elif separator and key in {"hero", "hero_image"}:
            hero = original_value
        elif normalized in {"silent", "no_sound", "nosound"}:
            silent = True
            sound = "default"
        elif normalized in {"sound", "with_sound"}:
            silent = False
            sound = "default"
        elif normalized in {"long", "long_duration"}:
            duration = "long"
        elif normalized in {"short", "short_duration"}:
            duration = "short"
        else:
            remainder_start = index
            break
    else:
        remainder_start = len(tokens)

    remainder = " ".join(tokens[remainder_start:]).strip()
    if remainder:
        if "|" in remainder:
            title_text, message_text = remainder.split("|", 1)
            title = title_text.strip() or title
            message = message_text.strip() or message
        else:
            title = remainder

    settings = SimpleNamespace(
        title=title,
        message=message,
        app_id=app_id,
        app_name=app_name,
        duration=duration,
        scenario=scenario,
        silent=silent,
        sound=sound,
        attribution=attribution,
        logo=logo,
        hero=hero,
    )
    return settings


def _print_windows_notification_help() -> None:
    print()
    print("Modern Windows toast command:")
    print("  notify [options] title | message")
    print("  notify_status")
    print()
    print("Options must come before the title:")
    print("  app_id=<id>                         optional AppUserModelID; default uses PowerShell identity")
    print("  app_name=<name|terminal>            register/use a toast banner name; overrides app_id")
    print("  duration=short|long                 toast duration")
    print("  scenario=default|alarm|reminder|incomingCall")
    print("  sound=default|mail|sms|reminder|alarm|call")
    print("  silent|no_sound|nosound             suppress notification sound")
    print("  sound                               allow notification sound")
    print("  attribution=<text>                  attribution line without spaces")
    print("  logo=<path_or_uri>                  app logo image")
    print("  hero=<path_or_uri>                  wide hero image")
    print()
    print("Examples:")
    print("  notify Build finished | Your script completed.")
    print("  notify app_name=terminal Build finished | Your script completed.")
    print("  notify silent Build finished | Your script completed.")
    print("  notify duration=long scenario=reminder Reminder | Check the terminal output.")
    print("  notify sound=mail logo=C:\\path\\icon.png Mail | New message received.")


def _print_windows_notification_status(app_id: str | None = None) -> None:
    app_id = str(app_id or "").strip()
    reason = get_windows_notification_disabled_reason(app_id)
    if reason is None:
        if app_id:
            print(f"Windows notifications enabled for {app_id!r}.")
        else:
            print("Windows notifications enabled globally.")
    else:
        if app_id:
            print(f"Windows notifications disabled for {app_id!r}: {reason}")
        else:
            print(f"Windows notifications disabled: {reason}")


def _print_commands(context) -> None:
    print()
    print("Commands:")
    print("  enable_always_on_top         make window topmost")
    print("  disable_resize               remove resizable border")
    print("  hide_title_bar               hide classic title bar")
    print("  disable_minimize_button      remove classic minimize button")
    print("  disable_maximize_button      remove classic maximize button")
    print("  disable_x_button             disable classic close/X command")
    print("  enable_x_button              restore classic close/X command")
    print("  enable_minimize_to_tray      hide to tray when minimized")
    print("  notify [options] title | msg show modern Windows toast")
    print("  notify_status                check whether Windows toast notifications are enabled")
    print("  notify_help                  print modern toast options")
    print("  ascii [font] message print message using a local ASCII font")
    print("  opacity 0-100                set whole-window opacity")
    print("  foreground                   restore, bring to top, request foreground")
    print("  taskbar_alarm                flash caption/taskbar until foreground")
    print("  flash_taskbar [count]        flash caption/taskbar count times")
    print("  border_color #RRGGBB         set DWM border/outline color")
    print("  caption_color #RRGGBB        set DWM caption color")
    print("  text_color #RRGGBB           set DWM caption text color")


def _run_command(command: str, context) -> bool:
    raw_command = command

    parts = raw_command.split()
    command = parts[0].lower().replace("-", "_")
    args = parts[1:]

    def require_arg(name: str) -> str:
        if not args:
            raise ValueError(f"{name} needs an argument.")
        return args[0]

    def notification_command() -> None:
        argument_text = raw_command[len(parts[0]) :].strip()
        settings = _parse_modern_toast_settings(
            argument_text,
            default_title=context.window.title or "Python notification",
        )
        if settings.app_name.lower() in {"terminal", "terminal_title", "window", "window_title"}:
            settings.app_name = context.window.title or "Python notification"

        show_modern_windows_notification(settings)

    def notification_status_command() -> None:
        app_id = ""
        if args:
            first = args[0]
            key, separator, value = first.partition("=")
            if separator and key.lower().replace("-", "_") in {"app_id", "appid", "aumid"}:
                app_id = value
            else:
                app_id = first
        _print_windows_notification_status(app_id)

    def ascii_message_command() -> None:
        argument_text = raw_command[len(parts[0]) :].strip()
        font_name, message = _parse_ascii_message_command(argument_text)
        print_in_ASCII_font(message, font_name)

    def opacity_command() -> None:
        set_window_opacity(int(require_arg("opacity")), context.window)

    def flash_taskbar_command() -> None:
        count = int(args[0]) if args else 5
        flash_taskbar(context.window, count=count, until_foreground=False)

    def taskbar_alarm_command() -> None:
        flash_taskbar(context.window, count=0, until_foreground=True)

    def border_color_command() -> None:
        set_frame_border_color(require_arg("border_color"), context.window)

    def caption_color_command() -> None:
        set_frame_caption_color(require_arg("caption_color"), context.window)

    def text_color_command() -> None:
        set_frame_text_color(require_arg("text_color"), context.window)

    commands = {
        "enable_always_on_top": lambda: set_always_on_top(True, context.window),
        "disable_resize": lambda: set_resize_disabled(True, context.window),
        "hide_title_bar": lambda: set_title_bar_hidden(True, context.window),
        "disable_minimize_button": lambda: set_minimize_button_disabled(True, context.window),
        "disable_maximize_button": lambda: set_maximize_button_disabled(True, context.window),
        "disable_x_button": lambda: set_x_button_disabled(True, context.window),
        "enable_x_button": lambda: set_x_button_disabled(False, context.window),
        "enable_minimize_to_tray": lambda: _ensure_tray_controller(context),
        "notify": notification_command,
        "notify_status": notification_status_command,
        "notify_help": _print_windows_notification_help,
        "ascii": ascii_message_command,
        "opacity": opacity_command,
        "foreground": lambda: restore_and_foreground_window(context.window),
        "flash_taskbar": flash_taskbar_command,
        "border_color": border_color_command,
        "outline_color": border_color_command,
        "caption_color": caption_color_command,
        "title_color": caption_color_command,
        "text_color": text_color_command,
        "title_text_color": text_color_command,
    }

    action = commands.get(command)
    if action is None:
        print(f"Unknown command: {command!r}")
        return True

    try:
        action()
    except Exception as error:
        print(f"Error: {error}")
        return True

    print(f"Done: {raw_command}")
    return True


def main() -> None:
    """Run the interactive terminal window-control smoke test."""

    tray_icon = r"C:\Users\Flo\Documents\Repositories\PyApp Template\code\backend\icons\icon.ico"

    window = get_terminal_window()
    context = SimpleNamespace(window=window, tray_icon_path=tray_icon, tray_controller=None)
    _print_commands(context)

    while True:
        command = input("> ")
        if not _run_command(command, context):
            break


if __name__ == "__main__":
    main()
