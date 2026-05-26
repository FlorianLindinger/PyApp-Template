def set_window_dwm_color(hwnd: int, attribute: int, rgb: tuple[int, int, int]) -> None:
    """Set one Windows DWM color attribute on a window."""

    import ctypes

    red, green, blue = rgb
    colorref = red | (green << 8) | (blue << 16)
    color = ctypes.c_uint(colorref)

    result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
        ctypes.c_void_p(hwnd),
        ctypes.c_uint(attribute),
        ctypes.byref(color),
        ctypes.sizeof(color),
    )

    if result != 0:
        raise OSError(f"DwmSetWindowAttribute failed with HRESULT {result:#x}")


DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36

# more DWMWA option???


set_window_dwm_color(get_candidate_hwnds()[0], DWMWA_CAPTION_COLOR, (255, 0, 0))
set_window_dwm_color(get_candidate_hwnds()[0], DWMWA_TEXT_COLOR, (255, 255, 255))
set_window_dwm_color(get_candidate_hwnds()[0], DWMWA_BORDER_COLOR, (255, 0, 0))


class TaskbarProgress:
    """Control Windows taskbar progress without using comtypes."""

    NOPROGRESS = 0x0
    INDETERMINATE = 0x1
    NORMAL = 0x2
    ERROR = 0x4
    PAUSED = 0x8

    def __init__(self) -> None:
        import ctypes
        import os
        import uuid
        from ctypes import wintypes

        if os.name != "nt":
            raise OSError("TaskbarProgress only works on Windows.")

        self._ctypes = ctypes
        self._wintypes = wintypes
        self._ole32 = ctypes.windll.ole32
        self._ptr = ctypes.c_void_p()
        self._must_uninitialize_com = False

        HRESULT = ctypes.c_long
        DWORD = wintypes.DWORD

        class GUID(ctypes.Structure):
            """Windows GUID/UUID structure used by COM."""

            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8),
            ]

            @classmethod
            def from_string(cls, value: str):
                parsed = uuid.UUID(value)
                data4 = (parsed.clock_seq_hi_variant, parsed.clock_seq_low)
                data4 += tuple(parsed.node.to_bytes(6, "big"))

                return cls(
                    parsed.time_low,
                    parsed.time_mid,
                    parsed.time_hi_version,
                    (ctypes.c_ubyte * 8)(*data4),
                )

        self._GUID = GUID
        self._HRESULT = HRESULT

        # COM IDs for CLSID_TaskbarList and IID_ITaskbarList3.
        clsid_taskbar_list = GUID.from_string("{56FDF344-FD6D-11d0-958A-006097C9A090}")
        iid_taskbar_list_3 = GUID.from_string("{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}")

        COINIT_APARTMENTTHREADED = 0x2
        CLSCTX_INPROC_SERVER = 0x1
        RPC_E_CHANGED_MODE = -2147417850

        self._ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, DWORD]
        self._ole32.CoInitializeEx.restype = HRESULT

        self._ole32.CoCreateInstance.argtypes = [
            ctypes.POINTER(GUID),
            ctypes.c_void_p,
            DWORD,
            ctypes.POINTER(GUID),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self._ole32.CoCreateInstance.restype = HRESULT

        # Initialize COM on this thread. If another mode is already active,
        # keep using it instead of failing.
        hr = self._ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)

        if hr in (0, 1):  # S_OK or S_FALSE
            self._must_uninitialize_com = True
        elif hr != RPC_E_CHANGED_MODE:
            self._raise_hresult(hr, "CoInitializeEx failed")

        hr = self._ole32.CoCreateInstance(
            ctypes.byref(clsid_taskbar_list),
            None,
            CLSCTX_INPROC_SERVER,
            ctypes.byref(iid_taskbar_list_3),
            ctypes.byref(self._ptr),
        )
        self._raise_hresult(hr, "CoCreateInstance(CLSID_TaskbarList) failed")

        # COM object vtable. Method indexes are fixed by ITaskbarList3 layout.
        self._vtable = ctypes.cast(
            self._ptr,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)),
        ).contents

        # ITaskbarList::HrInit, vtable index 3.
        hr_init = self._method(3, HRESULT)
        self._raise_hresult(hr_init(self._ptr), "ITaskbarList3.HrInit failed")

    def _raise_hresult(self, hr: int, message: str) -> None:
        """Raise OSError if a COM HRESULT indicates failure."""

        if hr < 0:
            raise OSError(f"{message}: HRESULT 0x{hr & 0xFFFFFFFF:08X}")

    def _method(self, index: int, restype, *argtypes):
        """Return a callable COM method from the ITaskbarList3 vtable."""

        return self._ctypes.WINFUNCTYPE(
            restype,
            self._ctypes.c_void_p,
            *argtypes,
        )(self._vtable[index])

    def set_state(self, hwnd: int, state: int) -> None:
        """Set the taskbar progress state."""

        # ITaskbarList3::SetProgressState, vtable index 10.
        method = self._method(
            10,
            self._HRESULT,
            self._wintypes.HWND,
            self._ctypes.c_int,
        )

        hr = method(self._ptr, hwnd, state)
        self._raise_hresult(hr, "SetProgressState failed")

    def set_value(self, hwnd: int, value: int = 100, total: int = 100) -> None:
        """Show normal determinate taskbar progress."""

        # ITaskbarList3::SetProgressValue, vtable index 9.
        method = self._method(
            9,
            self._HRESULT,
            self._wintypes.HWND,
            self._ctypes.c_ulonglong,
            self._ctypes.c_ulonglong,
        )

        hr = method(self._ptr, hwnd, value, total)
        self._raise_hresult(hr, "SetProgressValue failed")

        self.set_state(hwnd, self.NORMAL)

    def set_indeterminate(self, hwnd: int) -> None:
        """Show animated unknown-duration progress."""

        self.set_state(hwnd, self.INDETERMINATE)

    def set_error(self, hwnd: int, value: int = 100, total: int = 100) -> None:
        """Show red error progress."""

        self.set_value(hwnd, value, total)
        self.set_state(hwnd, self.ERROR)

    def set_paused(self, hwnd: int, value: int = 100, total: int = 100) -> None:
        """Show yellow paused progress."""

        self.set_value(hwnd, value, total)
        self.set_state(hwnd, self.PAUSED)

    def clear(self, hwnd: int) -> None:
        """Remove taskbar progress."""

        self.set_state(hwnd, self.NOPROGRESS)

    def close(self) -> None:
        """Release the COM object."""

        if self._ptr:
            # IUnknown::Release, vtable index 2.
            release = self._method(2, self._ctypes.c_ulong)
            release(self._ptr)
            self._ptr = None

        if self._must_uninitialize_com:
            self._ole32.CoUninitialize()
            self._must_uninitialize_com = False

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.close()


test = TaskbarProgress()
hwnd = get_candidate_hwnds()[0]
import time

# for _ in range(10):
test.set_error(hwnd, 100)
time.sleep(0.1)
test.set_error(hwnd, 80)
time.sleep(0.1)
test.set_error(hwnd, 60)
time.sleep(0.1)
test.set_error(hwnd, 40)
time.sleep(0.1)
test.set_error(hwnd, 20)
time.sleep(0.1)
test.set_error(hwnd, 0)
time.sleep(0.1)

test.set_indeterminate(hwnd)
time.sleep(1)

test.set_value(hwnd)
time.sleep(1)
test.set_paused(hwnd)
time.sleep(1)

for _ in range(10):
    test.set_paused(hwnd)
    time.sleep(0.7)
    test.set_error(hwnd, 50)
    time.sleep(0.7)


def flash_window(hwnd: int, count: int = 0, timeout_ms: int = 0) -> None:
    """Flash a window's taskbar button and caption.

    Args:
        hwnd:
            Native window handle.
        count:
            Number of flashes. Use 0 to flash until the window comes to foreground.
        timeout_ms:
            Flash interval in milliseconds. Use 0 for the system default.
    """

    import ctypes
    from ctypes import wintypes

    FLASHW_STOP = 0x00000000
    FLASHW_CAPTION = 0x00000001
    FLASHW_TRAY = 0x00000002
    FLASHW_ALL = FLASHW_CAPTION | FLASHW_TRAY
    FLASHW_TIMERNOFG = 0x0000000C  # Keep flashing until window becomes foreground.

    class FLASHWINFO(ctypes.Structure):
        """Structure passed to the Windows FlashWindowEx API."""

        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("hwnd", wintypes.HWND),
            ("dwFlags", wintypes.DWORD),
            ("uCount", wintypes.UINT),
            ("dwTimeout", wintypes.DWORD),
        ]

    info = FLASHWINFO(
        cbSize=ctypes.sizeof(FLASHWINFO),
        hwnd=hwnd,
        dwFlags=FLASHW_ALL | FLASHW_TIMERNOFG,
        uCount=count,
        dwTimeout=timeout_ms,
    )

    if not ctypes.windll.user32.FlashWindowEx(ctypes.byref(info)):
        raise ctypes.WinError()


test.set_error(get_candidate_hwnds()[0])


flash_window(get_candidate_hwnds()[0])

input()


# need highöight instaef of flash function?