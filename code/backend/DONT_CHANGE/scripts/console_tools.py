"""Windows console appearance and interactive messages."""

import os
import sys
from typing import Any, TextIO

ANSI_WARN = "\x1b[1;37;41m"
ANSI_SUCCESS = "\x1b[1;37;42m"
ANSI_RESET = "\033[0m"


def print_warn(msg: Any, sep: str | None = " ", end: str | None = "\n") -> None:
    """Print a warning-styled console message."""
    if msg is not None:
        print(f"{ANSI_WARN}{msg}{ANSI_RESET}", sep=sep, end=end)


def input_warn(msg: str) -> str:
    """Prompt for input using warning console styling."""
    return input(f"{ANSI_WARN}{msg}{ANSI_RESET}")


def input_success(msg: str) -> str:
    """Prompt for input using success console styling."""
    return input(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}")


def print_success(msg: Any, sep: str | None = " ", end: str | None = "\n") -> None:
    """Print a success-styled console message."""
    if msg is not None:
        print(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}", sep=sep, end=end)


def close_terminal(exit_code: Any = None) -> bool:
    """Exit this script only. Its owning batch/console decides whether to close."""
    raise SystemExit(exit_code)


def get_terminal_title() -> str:
    """Returns "" if it fails to get the title."""

    import ctypes

    try:
        buffer = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))
        return str(buffer.value)
    except Exception:
        return ""


def set_terminal_title(title: str | None) -> None:
    if title is None:
        return

    try:
        import ctypes

        clean_name = title.replace("\r\n", "").replace("\r", "")
        ctypes.windll.kernel32.SetConsoleTitleW(clean_name)
    except Exception:
        pass


def set_terminal_icon(icon_path: str | None) -> None:
    """Best-effort icon update of the current Windows terminal icon"""
    if icon_path in ("", None):
        return
    else:
        icon_path = os.path.normpath(icon_path)

    import ctypes
    from ctypes import wintypes

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type:ignore
        hwnd = int(kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return

        user32 = ctypes.WinDLL("user32", use_last_error=True)

        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.SendMessageW.argtypes = [
            wintypes.HWND,
            ctypes.c_uint,
            ctypes.c_size_t,
            ctypes.c_size_t,
        ]
        user32.SendMessageW.restype = ctypes.c_size_t
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL

        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE = 0x0040
        SM_CXSMICON = 49
        SM_CYSMICON = 50
        SM_CXICON = 11
        SM_CYICON = 12
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        def _load_icon(width: int, height: int) -> int:
            icon = user32.LoadImageW(None, icon_path, IMAGE_ICON, width, height, LR_LOADFROMFILE)
            if not icon:
                icon = user32.LoadImageW(None, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
            return int(icon or 0)

        small_icon = _load_icon(
            user32.GetSystemMetrics(SM_CXSMICON),
            user32.GetSystemMetrics(SM_CYSMICON),
        )
        large_icon = _load_icon(
            user32.GetSystemMetrics(SM_CXICON),
            user32.GetSystemMetrics(SM_CYICON),
        )
        if small_icon == 0 and large_icon == 0:
            return

        if small_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small_icon)
        if large_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, large_icon)
        user32.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )

    except Exception:
        pass


def set_terminal_app_id(app_id: str) -> None:
    """Try to set System.AppUserModel.ID on the terminal window itself."""

    if not app_id:
        return

    import ctypes
    import uuid
    from ctypes import wintypes

    HRESULT = ctypes.c_long
    VT_LPWSTR = 31
    S_OK = 0
    S_FALSE = 1
    RPC_E_CHANGED_MODE = 0x80010106

    def _helper_refresh_nonclient_area(hwnd: int) -> None:
        """Run the helper refresh nonclient area step."""
        user32_DLL = ctypes.WinDLL("user32", use_last_error=True)

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        user32_DLL.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )

    class _GUID(ctypes.Structure):
        """Represent a Windows GUID/UUID structure used by COM APIs."""

        _fields_ = (
            ("Data1", ctypes.c_ulong),
            ("Data2", ctypes.c_ushort),
            ("Data3", ctypes.c_ushort),
            ("Data4", ctypes.c_ubyte * 8),
        )

    class _PROPERTYKEY(ctypes.Structure):
        """WIP"""

        _fields_ = (("fmtid", _GUID), ("pid", wintypes.DWORD))

    class _PROPVARIANT(ctypes.Structure):
        """WIP"""

        _fields_ = (
            ("vt", ctypes.c_ushort),
            ("wReserved1", ctypes.c_ushort),
            ("wReserved2", ctypes.c_ushort),
            ("wReserved3", ctypes.c_ushort),
            ("pwszVal", ctypes.c_wchar_p),
        )

    class _IPropertyStore(ctypes.Structure):
        """WIP"""

    IPropertyStorePtr = ctypes.POINTER(_IPropertyStore)

    class _IPropertyStoreVtbl(ctypes.Structure):
        """WIP"""

        _fields_ = (
            (
                "QueryInterface",
                ctypes.WINFUNCTYPE(
                    HRESULT,
                    IPropertyStorePtr,
                    ctypes.POINTER(_GUID),
                    ctypes.POINTER(ctypes.c_void_p),
                ),
            ),
            ("AddRef", ctypes.WINFUNCTYPE(ctypes.c_ulong, IPropertyStorePtr)),
            ("Release", ctypes.WINFUNCTYPE(ctypes.c_ulong, IPropertyStorePtr)),
            (
                "GetCount",
                ctypes.WINFUNCTYPE(HRESULT, IPropertyStorePtr, ctypes.POINTER(wintypes.DWORD)),
            ),
            (
                "GetAt",
                ctypes.WINFUNCTYPE(
                    HRESULT,
                    IPropertyStorePtr,
                    wintypes.DWORD,
                    ctypes.POINTER(_PROPERTYKEY),
                ),
            ),
            (
                "GetValue",
                ctypes.WINFUNCTYPE(
                    HRESULT,
                    IPropertyStorePtr,
                    ctypes.POINTER(_PROPERTYKEY),
                    ctypes.POINTER(_PROPVARIANT),
                ),
            ),
            (
                "SetValue",
                ctypes.WINFUNCTYPE(
                    HRESULT,
                    IPropertyStorePtr,
                    ctypes.POINTER(_PROPERTYKEY),
                    ctypes.POINTER(_PROPVARIANT),
                ),
            ),
            ("Commit", ctypes.WINFUNCTYPE(HRESULT, IPropertyStorePtr)),
        )

    _IPropertyStore._fields_ = [("lpVtbl", ctypes.POINTER(_IPropertyStoreVtbl))]

    def _make_guid(value: str) -> _GUID:
        """Build and return the guid."""
        parsed = uuid.UUID(value)
        return _GUID(
            parsed.time_low,
            parsed.time_mid,
            parsed.time_hi_version,
            (ctypes.c_ubyte * 8)(*parsed.bytes[8:]),
        )

    def _format_hresult(hr: int) -> str:
        code = hr & 0xFFFFFFFF
        try:
            message = ctypes.FormatError(code).strip()
        except Exception:
            message = "unknown error"
        return f"0x{code:08X}: {message}"

    def _check_hresult(hr: int, action: str) -> None:
        if hr < 0:
            raise OSError(f"{action} failed with HRESULT {_format_hresult(hr)}")

    try:
        hwnd = int(ctypes.windll.kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return

        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        ole32 = ctypes.WinDLL("ole32", use_last_error=True)

        shell32.SHGetPropertyStoreForWindow.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(_GUID),
            ctypes.POINTER(IPropertyStorePtr),
        ]
        shell32.SHGetPropertyStoreForWindow.restype = HRESULT

        ole32.CoInitialize.argtypes = [ctypes.c_void_p]
        ole32.CoInitialize.restype = HRESULT
        ole32.CoUninitialize.argtypes = []
        ole32.CoUninitialize.restype = None

        iid_property_store = _make_guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")
        pkey_app_user_model_id = _PROPERTYKEY(
            _make_guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"),
            5,
        )
        prop_var = _PROPVARIANT()
        prop_var.vt = VT_LPWSTR
        prop_var.pwszVal = app_id

        coinitialize_result = ole32.CoInitialize(None)
        should_uninitialize = coinitialize_result in {S_OK, S_FALSE}
        if coinitialize_result < 0 and (coinitialize_result & 0xFFFFFFFF) != RPC_E_CHANGED_MODE:
            raise OSError(f"CoInitialize failed with HRESULT {_format_hresult(coinitialize_result)}")

        try:
            property_store = IPropertyStorePtr()
            hr = shell32.SHGetPropertyStoreForWindow(
                wintypes.HWND(hwnd),
                ctypes.byref(iid_property_store),
                ctypes.byref(property_store),
            )
            _check_hresult(hr, f"SHGetPropertyStoreForWindow for hwnd 0x{hwnd:016X}")

            try:
                hr = property_store.contents.lpVtbl.contents.SetValue(
                    property_store,
                    ctypes.byref(pkey_app_user_model_id),
                    ctypes.byref(prop_var),
                )
                _check_hresult(hr, f"SetValue System.AppUserModel.ID for hwnd 0x{hwnd:016X}")

                hr = property_store.contents.lpVtbl.contents.Commit(property_store)
                _check_hresult(hr, f"Commit System.AppUserModel.ID for hwnd 0x{hwnd:016X}")

                _helper_refresh_nonclient_area(hwnd)
            finally:
                if property_store:
                    property_store.contents.lpVtbl.contents.Release(property_store)
        finally:
            if should_uninitialize:
                ole32.CoUninitialize()
    except Exception:
        pass


def unminimize_terminal() -> None:
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        hwnd = int(kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return
        ctypes.windll.user32.ShowWindow(hwnd, 9)  # 9 means unminimized
    except Exception:
        pass


def foreground_terminal() -> None:
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        hwnd = int(kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def enable_unminimize_and_foreground_terminal_on_first_print() -> None:
    class unminimize_plus_foreground_terminal_on_first_output:
        """Unminimize a minimized terminal and set to foreground when output is written for the first time."""

        def __init__(self, stream: TextIO) -> None:
            self.stream = stream
            self._restored = False

        def _restore_if_needed(self, data: object) -> None:
            if self._restored or data in ("", b""):
                return
            self._restored = True
            unminimize_terminal()
            foreground_terminal()

        def write(self, data: str) -> int:
            """Write text to the wrapped stream or terminal target."""
            self._restore_if_needed(data)
            return self.stream.write(data)

        def flush(self) -> None:
            """Flush the wrapped stream when supported."""
            if hasattr(self.stream, "flush"):
                self.stream.flush()

        def isatty(self) -> bool:
            """Return whether the wrapped stream behaves like a terminal."""
            return bool(getattr(self.stream, "isatty", lambda: False)())

        def writable(self) -> bool:
            """Return whether the wrapped stream accepts writes."""
            return True

        def fileno(self) -> int:
            """Return the wrapped stream file descriptor."""
            if hasattr(self.stream, "fileno"):
                return self.stream.fileno()
            raise OSError("Underlying stream does not support fileno()")

        def __getattr__(self, name: str) -> Any:
            """Forward unknown attribute lookups to the wrapped stream."""
            return getattr(self.stream, name)

    # this will unminimize and foreground on first print/error
    sys.stdout = unminimize_plus_foreground_terminal_on_first_output(sys.stdout)  # type:ignore
    sys.stderr = unminimize_plus_foreground_terminal_on_first_output(sys.stderr)  # type:ignore


def set_terminal_colors(colors: str | None) -> None:
    """colors is in format of windows terminal colors"""
    if colors:
        try:
            import subprocess

            subprocess.run(["cmd.exe", "/c", "color", colors], check=False)
        except Exception:
            pass
