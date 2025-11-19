import ctypes
import ctypes.wintypes
import threading
import time

# Windows API Constants
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_USER = 0x400
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
IDI_APPLICATION = 32512
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x00000010

# Define WNDPROCTYPE first
# LRESULT is LONG_PTR, which varies by arch. c_ssize_t is the correct Python equivalent.
LRESULT = ctypes.c_ssize_t 
WNDPROCTYPE = ctypes.WINFUNCTYPE(LRESULT, ctypes.wintypes.HWND, ctypes.c_uint, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)

# Define argtypes for DefWindowProcA to prevent 64-bit truncation/overflow
ctypes.windll.user32.DefWindowProcA.argtypes = [ctypes.wintypes.HWND, ctypes.c_uint, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM]
ctypes.windll.user32.DefWindowProcA.restype = LRESULT

class WNDCLASS(ctypes.Structure):
    _fields_ = [("style", ctypes.c_uint),
                ("lpfnWndProc", WNDPROCTYPE),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", ctypes.wintypes.HINSTANCE),
                ("hIcon", ctypes.wintypes.HICON),
                ("hCursor", ctypes.wintypes.HICON),
                ("hbrBackground", ctypes.wintypes.HBRUSH),
                ("lpszMenuName", ctypes.c_char_p),
                ("lpszClassName", ctypes.c_char_p)]

class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("hWnd", ctypes.wintypes.HWND),
        ("uID", ctypes.c_uint),
        ("uFlags", ctypes.c_uint),
        ("uCallbackMessage", ctypes.c_uint),
        ("hIcon", ctypes.wintypes.HICON),
        ("szTip", ctypes.c_char * 128),
        ("dwState", ctypes.c_uint),
        ("dwStateMask", ctypes.c_uint),
        ("szInfo", ctypes.c_char * 256),
        ("uTimeout", ctypes.c_uint),
        ("szInfoTitle", ctypes.c_char * 64),
        ("dwInfoFlags", ctypes.c_uint),
    ]

class SystemTrayIcon:
    def __init__(self, tooltip, on_click, icon_path=None):
        self.tooltip = tooltip.encode("utf-8")
        self.on_click = on_click
        self.icon_path = icon_path
        self.hwnd = None
        self.hicon = None
        self.thread = None
        self.running = False

    def _window_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_USER + 20:
            if lparam == WM_LBUTTONUP:
                if self.on_click:
                    self.on_click()
            elif lparam == WM_RBUTTONUP:
                # Right click - maybe show menu later?
                pass
        return ctypes.windll.user32.DefWindowProcA(hwnd, msg, wparam, lparam)

    def _create_window(self):
        self.wnd_proc = WNDPROCTYPE(self._window_proc)

        hinst = ctypes.windll.kernel32.GetModuleHandleA(None)
        class_name = b"SystemTrayIconPy"

        wnd_class = WNDCLASS()
        wnd_class.style = 0
        wnd_class.lpfnWndProc = self.wnd_proc
        wnd_class.cbClsExtra = 0
        wnd_class.cbWndExtra = 0
        wnd_class.hInstance = hinst
        wnd_class.hIcon = 0
        wnd_class.hCursor = 0
        wnd_class.hbrBackground = 0
        wnd_class.lpszMenuName = None
        wnd_class.lpszClassName = class_name
        
        ctypes.windll.user32.RegisterClassA(ctypes.byref(wnd_class))

        self.hwnd = ctypes.windll.user32.CreateWindowExA(
            0, class_name, b"SystemTrayWindow", 0, 0, 0, 0, 0, 0, 0, hinst, 0
        )
        
        # Load Icon
        if self.icon_path and isinstance(self.icon_path, str):
            try:
                # Load from file
                self.hicon = ctypes.windll.user32.LoadImageA(
                    0, 
                    self.icon_path.encode("utf-8"), 
                    IMAGE_ICON, 
                    0, 0, 
                    LR_LOADFROMFILE
                )
            except Exception:
                self.hicon = None
        
        if not self.hicon:
            # Load default application icon
            self.hicon = ctypes.windll.user32.LoadIconA(0, IDI_APPLICATION)

    def _add_icon(self):
        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP
        nid.uCallbackMessage = WM_USER + 20
        nid.hIcon = self.hicon
        nid.szTip = self.tooltip
        
        ctypes.windll.shell32.Shell_NotifyIconA(NIM_ADD, ctypes.byref(nid))

    def _remove_icon(self):
        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = self.hwnd
        nid.uID = 1
        ctypes.windll.shell32.Shell_NotifyIconA(NIM_DELETE, ctypes.byref(nid))

    def _run(self):
        self._create_window()
        self._add_icon()
        
        msg = ctypes.wintypes.MSG()
        self.running = True
        while self.running and ctypes.windll.user32.GetMessageA(ctypes.byref(msg), None, 0, 0) > 0:
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageA(ctypes.byref(msg))
        
        self._remove_icon()
        ctypes.windll.user32.DestroyWindow(self.hwnd)

    def show(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def hide(self):
        self.running = False
        if self.hwnd:
            ctypes.windll.user32.PostMessageA(self.hwnd, 0x0010, 0, 0) # WM_CLOSE
