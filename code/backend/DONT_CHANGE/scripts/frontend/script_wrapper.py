# ruff: noqa: UP030, UP032

"""WIP

This script must be compatible for Python 3.5+:
- No function, argument, variable, or class attribute annotations
- No "from __future__ import annotations"
- No f-strings, including rf/fr strings
- No modern typing syntax such as list[str] or str | None
- No dataclasses
- No walrus operator :=
- No positional-only parameter marker /
- No async generators or async comprehensions
- No underscores in numeric literals
- No pathlib/os.PathLike-only APIs; keep accepting plain strings
- No subprocess.run(..., capture_output=True) or text=True
- No breakpoint()
- No .astimezone() for datetime
"""

# {e} will be formatted to exception:
fail_message = "[Error] Failed during wrapper start: {e}"

try:
    # ==============================
    # import Python packages
    # ==============================

    import atexit
    import builtins
    import ctypes
    import faulthandler
    import os
    import re
    import runpy
    import sys
    import threading
    from ctypes import wintypes
    from datetime import datetime

    # ==============================
    # define local variables
    # ==============================

    ANSI_WARN = "\x1b[1;37;41m"  # white text, red bg, bold
    ANSI_SUCCESS = "\x1b[1;37;42m"  # white text, green bg, bold
    ANSI_RESET = "\033[0m"
    ANSI_ESCAPE_RE = re.compile(
        r"\x1b(?:"
        r"\[[0-?]*[ -/]*[@-~]"
        r"|\][^\x07]*(?:\x07|\x1b\\)"
        r"|[@-Z\\-_]"
        r")"
    )

    # used to print in new terminal window:
    SCRIPT_BASE = r"""
import os
import ctypes

ANSI_RESET = "\033[0m"
ANSI_WARN = "\x1b[1;37;41m"
ANSI_SUCCESS = "\x1b[1;37;42m"

def print_warn(msg, sep = " ", end = "\n"):
    print("{}{}{}".format(ANSI_WARN, msg, ANSI_RESET), sep=sep, end=end)

def input_warn(msg):
    return input("{}{}{}".format(ANSI_WARN, msg, ANSI_RESET))

def input_success(msg):
    return input("{}{}{}".format(ANSI_SUCCESS, msg, ANSI_RESET))

def set_terminal_name(name):
    try:
        clean_name=name.replace('\n', '').replace('\r', '')
        os.system("title {}".format(clean_name))
    except Exception:
        pass

def get_terminal_name():
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))
        return buffer.value
    except Exception:
        return "Terminal"
"""

    kernel32_DLL = ctypes.WinDLL("kernel32", use_last_error=True)
    user32_DLL = ctypes.WinDLL("user32", use_last_error=True)

    # ==============================
    # define local functions/classes
    # ==============================

    def string_to_bool(string):
        """Convert a string to a boolean value, interpreting "true" (case-insensitive) as True, "false" (case-insensitive) as False, and raising ValueError for other inputs."""

        lowered = string.lower()
        if lowered == "true":
            return True
        elif lowered == "false":
            return False
        else:
            message = "Cannot convert string to bool: {!r}".format(string)
            raise ValueError(message)

    def process_args(args):
        """Process the command-line arguments: The second element in the input is used as the empty argument indicator, and all occurrences of it in the arguments list are replaced with empty strings in the output list. The first element of the input is typically the script name and is included unchanged in the output."""

        EMPTY_ARG_INDICATOR = args[1]  # args[0] is script name
        out = []

        for elem in args:
            if elem == EMPTY_ARG_INDICATOR:
                out.append("")
            else:
                out.append(elem)

        return out

    def strip_ansi_escape_sequences(text):
        """Remove terminal ANSI escape sequences from text."""
        return ANSI_ESCAPE_RE.sub("", text)

    def print_warn(msg, sep=" ", end="\n"):
        """Print a warning-styled console message."""
        print("{}{}{}".format(ANSI_WARN, msg, ANSI_RESET), sep=sep, end=end)

    def input_warn(msg):
        """Prompt for input using warning console styling."""
        return input("{}{}{}".format(ANSI_WARN, msg, ANSI_RESET))

    def input_success(msg):
        """Prompt for input using success console styling."""
        return input("{}{}{}".format(ANSI_SUCCESS, msg, ANSI_RESET))

    def run_text_in_new_terminal_and_wait(text):
        import subprocess
        import sys

        subprocess.run(  # noqa:S603
            [sys.executable, "-X", "faulthandler", "-c", text], creationflags=subprocess.CREATE_NEW_CONSOLE
        )

    def _helper_refresh_nonclient_area(hwnd):
        """WIP"""
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

    def get_terminal_name():
        try:
            buffer = ctypes.create_unicode_buffer(1024)
            ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))
            return str(buffer.value)
        except Exception:
            return "Terminal"

    def minimize_current_console():
        try:
            hwnd = kernel32_DLL.GetConsoleWindow()
            if hwnd:
                user32_DLL.ShowWindow(hwnd, 2)
        except Exception:
            pass

    def restore_current_console():
        """WIP"""
        try:
            hwnd = kernel32_DLL.GetConsoleWindow()
            if hwnd:
                user32_DLL.ShowWindow(hwnd, 9)
        except Exception:
            pass

    def get_candidate_hwnds():
        candidate_hwnds = []

        def add(hwnd):
            if hwnd == 0 or not user32_DLL.IsWindow(hwnd) or hwnd in candidate_hwnds:
                return
            candidate_hwnds.append(hwnd)

        console_hwnd = int(kernel32_DLL.GetConsoleWindow() or 0)

        def get_console_title():
            buffer = ctypes.create_unicode_buffer(1024)
            title_length = kernel32_DLL.GetConsoleTitleW(buffer, len(buffer))
            if title_length == 0:
                return ""
            return buffer.value

        def get_root_owner(hwnd):
            GA_ROOTOWNER = 3
            if hwnd == 0:
                return 0
            return int(user32_DLL.GetAncestor(hwnd, GA_ROOTOWNER) or 0)

        console_title = get_console_title()

        add(console_hwnd)
        add(get_root_owner(console_hwnd))

        if console_title:
            hwnd_by_console_class = int(user32_DLL.FindWindowW("ConsoleWindowClass", console_title) or 0)
            add(hwnd_by_console_class)
            add(get_root_owner(hwnd_by_console_class))

            hwnd_by_title = int(user32_DLL.FindWindowW(None, console_title) or 0)
            add(hwnd_by_title)
            add(get_root_owner(hwnd_by_title))

        return candidate_hwnds

    def set_terminal_app_id_safe(candidate_hwnds, app_id):
        """Try to set System.AppUserModel.ID on the terminal window itself."""
        import uuid

        if app_id == "":
            return 0

        HRESULT = ctypes.c_long
        VT_LPWSTR = 31
        S_OK = 0
        S_FALSE = 1
        RPC_E_CHANGED_MODE = 0x80010106

        class GUID(ctypes.Structure):
            """WIP"""

            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        class PROPERTYKEY(ctypes.Structure):
            """WIP"""

            _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]

        class PROPVARIANT(ctypes.Structure):
            """WIP"""

            _fields_ = [
                ("vt", ctypes.c_ushort),
                ("wReserved1", ctypes.c_ushort),
                ("wReserved2", ctypes.c_ushort),
                ("wReserved3", ctypes.c_ushort),
                ("pwszVal", ctypes.c_wchar_p),
            ]

        class IPropertyStore(ctypes.Structure):
            """WIP"""

        IPropertyStorePtr = ctypes.POINTER(IPropertyStore)

        class IPropertyStoreVtbl(ctypes.Structure):
            """Describe the IPropertyStore COM vtable layout."""

            _fields_ = [
                (
                    "QueryInterface",
                    ctypes.WINFUNCTYPE(
                        HRESULT,
                        IPropertyStorePtr,
                        ctypes.POINTER(GUID),
                        ctypes.POINTER(ctypes.c_void_p),
                    ),
                ),
                ("AddRef", ctypes.WINFUNCTYPE(ctypes.c_ulong, IPropertyStorePtr)),
                ("Release", ctypes.WINFUNCTYPE(ctypes.c_ulong, IPropertyStorePtr)),
                ("GetCount", ctypes.WINFUNCTYPE(HRESULT, IPropertyStorePtr, ctypes.POINTER(wintypes.DWORD))),
                (
                    "GetAt",
                    ctypes.WINFUNCTYPE(
                        HRESULT,
                        IPropertyStorePtr,
                        wintypes.DWORD,
                        ctypes.POINTER(PROPERTYKEY),
                    ),
                ),
                (
                    "GetValue",
                    ctypes.WINFUNCTYPE(
                        HRESULT,
                        IPropertyStorePtr,
                        ctypes.POINTER(PROPERTYKEY),
                        ctypes.POINTER(PROPVARIANT),
                    ),
                ),
                (
                    "SetValue",
                    ctypes.WINFUNCTYPE(
                        HRESULT,
                        IPropertyStorePtr,
                        ctypes.POINTER(PROPERTYKEY),
                        ctypes.POINTER(PROPVARIANT),
                    ),
                ),
                ("Commit", ctypes.WINFUNCTYPE(HRESULT, IPropertyStorePtr)),
            ]

        IPropertyStore._fields_ = [("lpVtbl", ctypes.POINTER(IPropertyStoreVtbl))]

        def make_guid(value):
            """WIP"""
            parsed = uuid.UUID(value)
            return GUID(
                parsed.time_low,
                parsed.time_mid,
                parsed.time_hi_version,
                (ctypes.c_ubyte * 8)(*parsed.bytes[8:]),
            )

        def format_hresult(hr):
            code = hr & 0xFFFFFFFF
            try:
                message = ctypes.FormatError(code).strip()
            except Exception:
                message = "unknown error"
            return "0x{0:08X}: {1}".format(code, message)

        def check_hresult(hr, action):
            """WIP"""
            if hr < 0:
                message = "{0} failed with HRESULT {1}".format(action, format_hresult(hr))
                raise OSError(message)

        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        ole32 = ctypes.WinDLL("ole32", use_last_error=True)

        shell32.SHGetPropertyStoreForWindow.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(GUID),
            ctypes.POINTER(IPropertyStorePtr),
        ]
        shell32.SHGetPropertyStoreForWindow.restype = HRESULT

        ole32.CoInitialize.argtypes = [ctypes.c_void_p]
        ole32.CoInitialize.restype = HRESULT
        ole32.CoUninitialize.argtypes = []
        ole32.CoUninitialize.restype = None

        iid_property_store = make_guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")
        pkey_app_user_model_id = PROPERTYKEY(
            make_guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"),
            5,
        )
        prop_var = PROPVARIANT()
        prop_var.vt = VT_LPWSTR
        prop_var.pwszVal = app_id

        coinitialize_result = ole32.CoInitialize(None)
        should_uninitialize = coinitialize_result in {S_OK, S_FALSE}
        if coinitialize_result < 0 and (coinitialize_result & 0xFFFFFFFF) != RPC_E_CHANGED_MODE:
            message = "CoInitialize failed with HRESULT {0}".format(format_hresult(coinitialize_result))
            raise OSError(message)

        changed_count = 0
        try:
            for hwnd in candidate_hwnds:
                try:
                    property_store = IPropertyStorePtr()
                    hr = shell32.SHGetPropertyStoreForWindow(
                        wintypes.HWND(hwnd),
                        ctypes.byref(iid_property_store),
                        ctypes.byref(property_store),
                    )
                    check_hresult(hr, "SHGetPropertyStoreForWindow for hwnd 0x{0:016X}".format(hwnd))

                    try:
                        hr = property_store.contents.lpVtbl.contents.SetValue(
                            property_store,
                            ctypes.byref(pkey_app_user_model_id),
                            ctypes.byref(prop_var),
                        )
                        check_hresult(hr, "SetValue System.AppUserModel.ID for hwnd 0x{0:016X}".format(hwnd))

                        hr = property_store.contents.lpVtbl.contents.Commit(property_store)
                        check_hresult(hr, "Commit System.AppUserModel.ID for hwnd 0x{0:016X}".format(hwnd))

                        _helper_refresh_nonclient_area(hwnd)
                        changed_count += 1
                    finally:
                        if property_store:
                            property_store.contents.lpVtbl.contents.Release(property_store)
                except Exception as error:
                    print("[Info] AppID update skipped for hwnd 0x{0:016X}: {1}".format(hwnd, error))
        finally:
            if should_uninitialize:
                ole32.CoUninitialize()

        return changed_count

    def set_terminal_icon(candidate_hwnds, icon_path):

        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1

        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE = 0x0040

        SM_CXICON = 11
        SM_CYICON = 12
        SM_CXSMICON = 49
        SM_CYSMICON = 50
        GCLP_HICON = -14
        GCLP_HICONSM = -34
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_longlong):
            signed_ptr = ctypes.c_longlong
        else:
            signed_ptr = ctypes.c_long

        hinstance_type = getattr(wintypes, "HINSTANCE", wintypes.HANDLE)
        wparam_type = getattr(wintypes, "WPARAM", ctypes.c_size_t)
        lparam_type = getattr(wintypes, "LPARAM", signed_ptr)
        lresult_type = getattr(wintypes, "LRESULT", signed_ptr)

        kernel32_DLL.GetConsoleWindow.argtypes = []
        kernel32_DLL.GetConsoleWindow.restype = wintypes.HWND

        kernel32_DLL.GetConsoleTitleW.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
        kernel32_DLL.GetConsoleTitleW.restype = wintypes.DWORD

        kernel32_DLL.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32_DLL.OpenProcess.restype = wintypes.HANDLE

        kernel32_DLL.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32_DLL.QueryFullProcessImageNameW.restype = wintypes.BOOL

        kernel32_DLL.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32_DLL.CloseHandle.restype = wintypes.BOOL

        user32_DLL.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        user32_DLL.FindWindowW.restype = wintypes.HWND

        user32_DLL.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32_DLL.GetAncestor.restype = wintypes.HWND

        user32_DLL.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32_DLL.GetClassNameW.restype = ctypes.c_int

        user32_DLL.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32_DLL.GetSystemMetrics.restype = ctypes.c_int

        user32_DLL.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32_DLL.GetWindowTextLengthW.restype = ctypes.c_int

        user32_DLL.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32_DLL.GetWindowTextW.restype = ctypes.c_int

        user32_DLL.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32_DLL.GetWindowThreadProcessId.restype = wintypes.DWORD

        user32_DLL.IsWindow.argtypes = [wintypes.HWND]
        user32_DLL.IsWindow.restype = wintypes.BOOL

        user32_DLL.IsWindowVisible.argtypes = [wintypes.HWND]
        user32_DLL.IsWindowVisible.restype = wintypes.BOOL

        user32_DLL.LoadImageW.argtypes = [
            hinstance_type,
            wintypes.LPCWSTR,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32_DLL.LoadImageW.restype = wintypes.HANDLE

        user32_DLL.SendMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wparam_type,
            lparam_type,
        ]
        user32_DLL.SendMessageW.restype = lresult_type

        if hasattr(user32_DLL, "SetClassLongPtrW"):
            set_class_long = user32_DLL.SetClassLongPtrW
            set_class_long.argtypes = [wintypes.HWND, ctypes.c_int, signed_ptr]
            set_class_long.restype = ctypes.c_size_t
        else:
            set_class_long = user32_DLL.SetClassLongW
            set_class_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
            set_class_long.restype = wintypes.DWORD

        user32_DLL.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32_DLL.SetWindowPos.restype = wintypes.BOOL

        user32_DLL.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32_DLL.ShowWindow.restype = wintypes.BOOL

        def format_last_error(prefix):
            """Format the last error."""
            error_code = ctypes.get_last_error()
            if error_code == 0:
                return prefix
            return "{0} ({1}: {2})".format(prefix, error_code, ctypes.FormatError(error_code).strip())

        def get_window_text(hwnd):
            """Return the window text."""
            if hwnd == 0:
                return ""
            text_length = user32_DLL.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(text_length + 1)
            user32_DLL.GetWindowTextW(hwnd, buffer, len(buffer))
            return buffer.value

        def get_window_class_name(hwnd):
            if hwnd == 0:
                return ""
            buffer = ctypes.create_unicode_buffer(256)
            user32_DLL.GetClassNameW(hwnd, buffer, len(buffer))
            return buffer.value

        def get_window_process_id(hwnd):
            if hwnd == 0:
                return 0
            process_id = wintypes.DWORD()
            user32_DLL.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            return int(process_id.value)  # type:ignore

        def get_process_image_path(process_id):
            if process_id == 0:
                return ""

            process_handle = kernel32_DLL.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
            if not process_handle:
                return ""

            try:
                buffer_length = wintypes.DWORD(32768)
                buffer = ctypes.create_unicode_buffer(buffer_length.value)
                if kernel32_DLL.QueryFullProcessImageNameW(process_handle, 0, buffer, ctypes.byref(buffer_length)):
                    return buffer.value
                return ""
            finally:
                kernel32_DLL.CloseHandle(process_handle)

        def describe_window(hwnd):
            if hwnd == 0:
                return "hwnd=0x0"

            process_id = get_window_process_id(hwnd)
            return "hwnd=0x{0:016X}, class={1!r}, title={2!r}, visible={3}, pid={4}, process={5!r}".format(
                hwnd,
                get_window_class_name(hwnd),
                get_window_text(hwnd),
                bool(user32_DLL.IsWindowVisible(hwnd)),
                process_id,
                get_process_image_path(process_id),
            )

        def load_icon(path, width, height):
            icon_handle = user32_DLL.LoadImageW(None, path, IMAGE_ICON, width, height, LR_LOADFROMFILE)
            if not icon_handle:
                icon_handle = user32_DLL.LoadImageW(None, path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
            if not icon_handle:
                message = 'Failed to load icon from "{}"'.format(path)
                raise OSError(format_last_error(message))
            return int(icon_handle)

        def set_class_icon(hwnd, index, icon_handle):
            ctypes.set_last_error(0)
            set_class_long(hwnd, index, icon_handle)
            if ctypes.get_last_error() != 0:
                message = "Failed to update window class icon for hwnd 0x{0:016X}".format(hwnd)
                raise OSError(format_last_error(message))

        normalized_icon_path = os.path.abspath(os.path.expanduser(icon_path))
        if not os.path.isfile(normalized_icon_path):
            message = 'Icon file not found: "{}"'.format(normalized_icon_path)
            raise FileNotFoundError(message)

        if not candidate_hwnds:
            raise RuntimeError("Could not find the current terminal window.")

        small_icon = load_icon(
            normalized_icon_path,
            user32_DLL.GetSystemMetrics(SM_CXSMICON),
            user32_DLL.GetSystemMetrics(SM_CYSMICON),
        )
        large_icon = load_icon(
            normalized_icon_path,
            user32_DLL.GetSystemMetrics(SM_CXICON),
            user32_DLL.GetSystemMetrics(SM_CYICON),
        )

        for hwnd in candidate_hwnds:
            user32_DLL.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small_icon)
            user32_DLL.SendMessageW(hwnd, WM_SETICON, ICON_BIG, large_icon)
            try:
                set_class_icon(hwnd, GCLP_HICONSM, small_icon)
                set_class_icon(hwnd, GCLP_HICON, large_icon)
            except OSError:
                pass
            _helper_refresh_nonclient_area(hwnd)

    class pipe_splitter:
        """
        Mirror text output to a console stream and an optional log stream, with:
        - separate optional timestamp formats for console and log
        - optional red coloring for console error output only
        - line-aware prefixing so timestamps appear once per line

        Timestamp behavior:
        - if print_timestamp_format is "", None, or False -> no console timestamp
        - if log_timestamp_format is "", None, or False -> no log timestamp

        Example:
            import atexit
            import sys

            log_file = open("app.log", "w", encoding="utf-8", buffering=1)
            atexit.register(log_file.close)

            sys.stdout = pipe_splitter(
                print_stream=sys.__stdout__,
                log_stream=log_file,
                print_timestamp_format="%H:%M:%S",
                log_timestamp_format="%Y-%m-%d %H:%M:%S",
                print_red=False,
            )

            sys.stderr = pipe_splitter(
                print_stream=sys.__stderr__,
                log_stream=log_file,
                print_timestamp_format="%H:%M:%S",
                log_timestamp_format="%Y-%m-%d %H:%M:%S",
                print_red=True,
            )
        """

        ANSI_RED = "\x1b[31m"
        ANSI_RESET = "\x1b[0m"

        def __init__(
            self,
            print_stream,  # TextIO object
            log_stream=None,  # TextIO object or None
            *,
            print_timestamp_format="[%H:%M:%S] ",
            log_timestamp_format="[%H:%M:%S]\t",
            input_timestamp_format="",
            log_input_timestamp_format="",
            print_red=False,
            auto_flush=True,
        ):
            if print_stream is None:
                raise ValueError("print_stream is required")

            self.print_stream = print_stream
            self.log_stream = log_stream
            self.print_timestamp_format = print_timestamp_format
            self.log_timestamp_format = log_timestamp_format
            self.input_timestamp_format = input_timestamp_format
            self.log_input_timestamp_format = log_input_timestamp_format
            self.print_red = print_red
            self.auto_flush = auto_flush

            self._at_line_start = True
            self._lock = threading.RLock()  # needed if multiple threads want to print at same time

        def _timestamp_prefix(self, fmt):
            if not fmt:
                return ""
            return datetime.now().strftime(fmt)  # noqa:DTZ005

        def _print_supports_color(self):
            return bool(getattr(self.print_stream, "isatty", lambda: False)())

        def write(self, data):
            if data is None:
                data = ""
            if not isinstance(data, str):
                data = str(data)
            if data == "":
                return 0

            with self._lock:
                parts = data.splitlines(keepends=True)
                if not parts:
                    parts = [data]

                for part in parts:
                    if self._at_line_start:
                        print_prefix = self._timestamp_prefix(self.print_timestamp_format)
                        log_prefix = self._timestamp_prefix(self.log_timestamp_format)

                        if print_prefix:
                            self.print_stream.write(print_prefix)
                        if self.log_stream is not None and log_prefix:
                            self.log_stream.write(log_prefix)

                        if self.print_red and self._print_supports_color():
                            self.print_stream.write(self.ANSI_RED)

                    self.print_stream.write(part)
                    if self.log_stream is not None:
                        self.log_stream.write(strip_ansi_escape_sequences(part))

                    if part.endswith("\n"):
                        if self.print_red and self._print_supports_color():
                            self.print_stream.write(self.ANSI_RESET)
                        self._at_line_start = True
                    else:
                        self._at_line_start = False

                if self.auto_flush:
                    self.flush()

            return len(data)

        def write_input_prompt(self, prompt):
            """Write the input prompt."""
            if prompt is None:
                prompt = ""
            if not isinstance(prompt, str):
                prompt = str(prompt)

            with self._lock:
                print_prefix = self._timestamp_prefix(self.input_timestamp_format)
                log_prefix = self._timestamp_prefix(self.log_input_timestamp_format)

                self.print_stream.write("{}{}".format(print_prefix, prompt))
                if self.log_stream is not None:
                    self.log_stream.write("{}{}".format(log_prefix, strip_ansi_escape_sequences(prompt)))

                self._at_line_start = prompt.endswith("\n")
                if self.auto_flush:
                    self.flush()

        def complete_input_line(self, text):
            """Finish logging a user input line."""
            with self._lock:
                if self.log_stream is not None and not self._at_line_start:
                    self.log_stream.write("{}\n".format(text))
                self._at_line_start = True
                if self.auto_flush:
                    self.flush()

        def flush(self):
            with self._lock:
                if hasattr(self.print_stream, "flush"):
                    self.print_stream.flush()
                if self.log_stream is not None and hasattr(self.log_stream, "flush"):
                    self.log_stream.flush()

        def isatty(self):
            return bool(getattr(self.print_stream, "isatty", lambda: False)())

        def writable(self):
            return True

        def fileno(self):
            if hasattr(self.print_stream, "fileno"):
                return self.print_stream.fileno()
            raise OSError("Underlying print_stream does not support fileno()")

        @property
        def encoding(self):
            return getattr(self.print_stream, "encoding", None)

    def looks_like_interpreter_crash(returncode):
        """Return whether a process return code matches common Windows crash codes. A Python crash is meant to be a Python interpreter crash as opposed to a exit with a failure code for exampel with sys.exit(1)."""
        _WINDOWS_CRASH_CODES = {
            0xC0000005,  # access violation
            0xC00000FD,  # stack overflow
            0xC000001D,  # illegal instruction
            0xC0000096,  # privileged instruction
            0xC0000409,  # stack buffer overrun
        }

        def _int_to_unsigned32(n):
            """Convert a signed return code to an unsigned 32-bit value."""
            return n & 0xFFFFFFFF

        return isinstance(returncode, int) and (_int_to_unsigned32(returncode) in _WINDOWS_CRASH_CODES)

    def process_finish(wav_path="", log_path="", open_log=False):
        """Run completion side effects such as sounds and opening logs."""
        if wav_path:
            try:
                import winsound

                winsound.PlaySound(
                    wav_path,
                    winsound.SND_FILENAME | winsound.SND_NODEFAULT,
                )
            except Exception as e:
                print("[Error] Failed to play .wav file: {}".format(e))

        if log_path and open_log:
            try:
                os.startfile(log_path)  # type: ignore[attr-defined]  # noqa:S606
            except Exception as e:
                print("[Error] Failed to open log: {}".format(e))

    class _ProcessIdRegistry:
        """Maintain the PID file entries created by this launcher process."""

        def __init__(self, path):
            self.path = path
            self._process_ids = set()
            self._lock = threading.RLock()

        def add(self, process_id):
            """Add a pid value to the local collection when valid and new."""
            if self.path == "" or process_id <= 0:
                return

            with self._lock:
                if process_id in self._process_ids:
                    return
                self._process_ids.add(process_id)

                folder = os.path.dirname(self.path)
                if folder:
                    os.makedirs(folder, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as pid_file:
                    pid_file.write("{}\n".format(process_id))

        def remove(self, process_id):
            """Remove a value from the local collection and backing file."""
            if self.path == "" or process_id <= 0:
                return

            with self._lock:
                self._process_ids.discard(process_id)
                try:
                    with open(self.path, encoding="utf-8") as pid_file:
                        lines = pid_file.readlines()
                except FileNotFoundError:
                    return
                except Exception:
                    return

                remaining_lines = []
                process_id_text = str(process_id)
                for line in lines:
                    parts = line.strip().split(maxsplit=1)
                    if parts and parts[0] == process_id_text:
                        continue
                    remaining_lines.append(line)

                try:
                    if any(line.strip() for line in remaining_lines):
                        with open(self.path, "w", encoding="utf-8") as pid_file:
                            pid_file.writelines(remaining_lines)
                    else:
                        os.remove(self.path)
                except Exception:
                    pass

        def cleanup(self):
            """Remove registered process IDs during interpreter shutdown."""
            for process_id in list(self._process_ids):
                self.remove(process_id)

    def setup_log_prints(
        log_path,
        overwrite_log=True,
        print_prepend="",
        log_print_prepend="",
        input_prepend="",
        log_input_prepend="",
    ):
        """Install stdout, stderr, and input wrappers for logging."""
        global log_file  # type:ignore
        folder = os.path.dirname(log_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        log_file = open(log_path, "w" if overwrite_log else "a", encoding="utf-8", buffering=1)  # noqa:SIM115
        atexit.register(log_file.close)
        sys.stdout = pipe_splitter(
            sys.__stdout__,
            log_file,
            print_timestamp_format=print_prepend,
            log_timestamp_format=log_print_prepend,
            input_timestamp_format=input_prepend,
            log_input_timestamp_format=log_input_prepend,
        )
        sys.stderr = pipe_splitter(
            sys.__stderr__,
            log_file,
            print_timestamp_format=print_prepend,
            log_timestamp_format=log_print_prepend,
            input_timestamp_format=input_prepend,
            log_input_timestamp_format=log_input_prepend,
            print_red=True,
        )
        if faulthandler.is_enabled():
            faulthandler.enable(file=log_file, all_threads=True)

    # ==============================
    # define main function
    # ==============================

    def main():

        # ==============================
        # import and convert args

        (
            _script_name,
            _EMPTY_ARG_INDICATOR,
            app_id,
            log_path,
            close_on_crash,
            close_on_failure,
            close_on_success,
            icon_path,
            input_prepend,
            log_input_prepend,
            log_print_prepend,
            open_log_file_after_crash,
            open_log_file_after_failure,
            open_log_file_after_success,
            overwrite_log,
            print_prepend,
            program_name,
            python_script_path,
            wav_on_crash,
            wav_on_failure,
            wav_on_success,
            wdir_is_script_dir,
            CORRECT_START_SIGNAL_FILE_PATH,
            process_id_file_path,
            #
            # launch mode specific args:
            #
            terminal_colors,
            classic_terminal_cols,
            classic_terminal_lines,
            program_has_terminal,
        ) = process_args(sys.argv)

        # convert some to bools
        close_on_crash = string_to_bool(close_on_crash)
        close_on_failure = string_to_bool(close_on_failure)
        close_on_success = string_to_bool(close_on_success)
        open_log_file_after_crash = string_to_bool(open_log_file_after_crash)
        open_log_file_after_failure = string_to_bool(open_log_file_after_failure)
        open_log_file_after_success = string_to_bool(open_log_file_after_success)
        overwrite_log = string_to_bool(overwrite_log)
        wdir_is_script_dir = string_to_bool(wdir_is_script_dir)
        program_has_terminal = string_to_bool(program_has_terminal)

        # ==============================

        # tell the backend terminal via a signal file to close because successful start:
        if CORRECT_START_SIGNAL_FILE_PATH:
            folder = os.path.dirname(CORRECT_START_SIGNAL_FILE_PATH)
            if folder:
                os.makedirs(folder, exist_ok=True)
            open(CORRECT_START_SIGNAL_FILE_PATH, "w", encoding="utf-8").close()

        # add pid to "currently running" file:
        if process_id_file_path != "":
            try:
                process_id_registry = _ProcessIdRegistry(process_id_file_path)
                process_id_registry.add(os.getpid())
                atexit.register(process_id_registry.cleanup)
            except Exception as e:
                print("[Warning] Failed to write script-wrapper PID file: {}".format(e))

        # update terminal appearance if visible:
        if program_has_terminal:
            # set terminal name
            if program_name:
                os.system("title {}".format(program_name))  # noqa:S605

            os.system("color {}".format(terminal_colors))  # noqa:S605
            mode_parts = []
            if classic_terminal_cols:
                mode_parts.append("cols={}".format(classic_terminal_cols))
            if classic_terminal_lines != "":
                mode_parts.append("lines={}".format(classic_terminal_lines))
            if mode_parts:
                os.system("mode con: " + " ".join(mode_parts))  # noqa:S605

            # set terminal appearance in new thread because slow: terminal icon+appID (for taskabr grouping):
            def _set_terminal_icon_and_app_id():
                """set AppID, and icon."""
                try:
                    candidate_hwnds = get_candidate_hwnds()
                    set_terminal_icon(candidate_hwnds, icon_path)  # type:ignore
                    set_terminal_app_id_safe(candidate_hwnds, app_id)  # type:ignore

                except Exception as error:
                    print("[Error] During terminal appearance update: {}".format(error))

            terminal_appearance_thread = threading.Thread(target=_set_terminal_icon_and_app_id)
            terminal_appearance_thread.start()
        else:
            terminal_appearance_thread = None

        # needed in case main script spawns a GUI: For taskbar grouping (combining) of launched window into taskbar-pinned shortcut:
        if app_id:
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)  # type:ignore
            except Exception as e:
                print("[Info] Failed to set app id for taskbar grouping: {}".format(e))

        # set working directory:
        if wdir_is_script_dir:
            os.chdir(os.path.dirname(python_script_path))

        # setup logging:
        if log_path != "":
            setup_log_prints(
                log_path, overwrite_log, print_prepend, log_print_prepend, input_prepend, log_input_prepend
            )  # type:ignore

        # change pythons builtin "input" function:
        original_input = builtins.input
        if input_prepend != "" or log_input_prepend != "" or hasattr(sys.stdout, "complete_input_line"):

            def input_with_prepend(prompt=""):
                """Prompt for input while applying console and log prefixes."""
                if hasattr(sys.stdout, "write_input_prompt"):
                    sys.stdout.write_input_prompt(prompt)
                    text = original_input("")
                else:
                    text = original_input("{}{}".format(input_prepend, prompt))
                if hasattr(sys.stdout, "complete_input_line"):
                    sys.stdout.complete_input_line(text)
                return text

            builtins.input = input_with_prepend

        # define environemental variables to pass to main script:
        os.environ["PROGRAM_NAME"] = program_name
        os.environ["ICON_PATH"] = icon_path
        os.environ["LOG_PATH"] = log_path
        os.environ["APP_ID"] = app_id
        os.environ["PROGRAM_HAS_TERMINAL"] = "1" if program_has_terminal else "0"
        os.environ["WDIR_IS_SCRIPT_DIR"] = "1" if wdir_is_script_dir else "0"
        os.environ["CLOSE_ON_FAILURE"] = "1" if close_on_failure else "0"
        os.environ["CLOSE_ON_SUCCESS"] = "1" if close_on_success else "0"

        # change sys.path[0] to be dir of target script and not this script:
        sys.path[0] = os.path.dirname(python_script_path)

        # ==============================
        # run in the current python process and wait for finish

        try:
            runpy.run_path(python_script_path, run_name="__main__")
            exit_code = 0  # meaning no crash
        except SystemExit as e:  # catches sys.exit
            exit_code = e.code
            if exit_code is None:
                exit_code = 0
        except SyntaxError as e:  # catches synatx error in script_path or raised by script_path
            
            finished changes in main part: error handling
            
            
            
            
            # WIP!!

            import traceback

            print("-" * 20)

            # SyntaxError is special for older python versions: Python normally prints it without a normal traceback.
            if isinstance(e, SyntaxError):
                print("".join(traceback.format_exception_only(type(e), e)), end="")
            else:
                tb = e.__traceback__

                # Drop frames from this launcher/wrapper/runpy until the script's first frame.
                while tb is not None:
                    frame_path = os.path.abspath(tb.tb_frame.f_code.co_filename)

                    if frame_path == python_script_path:
                        break

                    tb = tb.tb_next

                traceback.print_exception(type(e), e, tb)

            print("-" * 20)
            print("".join(traceback.format_exception_only(type(e), e)), end="")

            print("-" * 20)
            print(traceback.format_exc())
            print("-" * 20)

            exit_code = 1
        except KeyboardInterrupt as e:
            exit_code = 1

        except BaseException as e:
            exit_code = 1

            import traceback

            print(traceback.format_exc())

        # # SyntaxError is special: Python normally prints it without a normal traceback.
        # if isinstance(error, SyntaxError):
        #     print("".join(traceback.format_exception_only(type(error), error)), end="")
        #     return

        # script_path = os.path.abspath(script_path)
        # tb = error.__traceback__

        # # Drop frames from this launcher/wrapper/runpy until the script's first frame.
        # while tb is not None:
        #     frame_path = os.path.abspath(tb.tb_frame.f_code.co_filename)

        #     if frame_path == script_path:
        #         break

        #     tb = tb.tb_next

        # traceback.print_exception(type(error), error, tb)

        finally:
            builtins.input = original_input
            if terminal_appearance_thread is not None:
                terminal_appearance_thread.join(timeout=5)  # timeout in s

        # ==============================

        # change terminal and print depending on exit_code
        if exit_code == 0:
            process_finish(wav_on_success, log_path, open_log_file_after_success)
            if close_on_success:
                sys.exit(0)
            else:
                script = (
                    SCRIPT_BASE
                    + """
set_terminal_name("[Success] " + get_terminal_name())
print()
input_success("[Program finished successfully] Press Enter to exit.")
"""
                )
                if program_has_terminal:
                    exec(script)  # noqa
                else:
                    if log_path != "":
                        print("[Program finished successfully]")
                    run_text_in_new_terminal_and_wait(script)
                sys.exit(0)

        elif looks_like_interpreter_crash(exit_code):
            process_finish(wav_on_crash, log_path, open_log_file_after_crash)
            if close_on_crash:
                sys.exit(exit_code)
            else:
                script = (
                    SCRIPT_BASE
                    + """
set_terminal_name("[Crash] " + get_terminal_name())
print()
print_warn('[Python Interpreter Crash] Script exited with Windows crash code: "' + {0!r} + '"')
input_warn("[Python Interpreter Crash] Press Enter to exit.")
""".format(str(exit_code))
                )
                if program_has_terminal:
                    exec(script)  # noqa
                else:
                    run_text_in_new_terminal_and_wait(script)
                sys.exit(exit_code)

        else:  # regular failure case (includes any string exit_code)
            process_finish(wav_on_failure, log_path, open_log_file_after_failure)
            if close_on_failure:
                sys.exit(exit_code)
            else:
                script = (
                    SCRIPT_BASE
                    + """
set_terminal_name("[Failure] " + get_terminal_name())
print()
print_warn("[Python Failure Return] Script exited with code: " + {0!r})
input_warn("[Python Failure Return] Press Enter to exit.")
""".format(str(exit_code))
                )
                if program_has_terminal:
                    exec(script)  # noqa
                else:
                    run_text_in_new_terminal_and_wait(script)

                sys.exit(exit_code)

    # ==============================
    # execute main function
    # ==============================

    if __name__ == "__main__":
        try:
            # setup_terminal_colors()
            # setup_unminimize_and_foreground_on_first_print()
            main()
        # except Exception as e:
        #     print_traceback(fail_message.format(e=e))
        #     input_warn("[Error] Press enter to exit")
        # close_terminal()

        # ==============================

        except Exception as e:  # backend crash
            import sys
            import traceback

            try:  # attempt detailed error report
                script = (
                    SCRIPT_BASE
                    + """
set_terminal_name("[Crash] " + get_terminal_name())
print()
print_warn("="*40)
print_warn("CRITICAL LAUNCH ERROR: " + {0!r})
print_warn("-"*40)
print_warn({1!r}, end="")
print_warn("-"*40)
print_warn("[Info] Python Exe: " + {2!r})
print_warn("[Info] Script: " + {3!r})
print_warn("-"*40)
input_warn("[Python Crash] See above. Press Enter to exit.")
""".format(str(e), traceback.format_exc(), sys.executable, python_script_path)
                )
                if program_has_terminal:
                    exec(script)  # noqa
                else:
                    run_text_in_new_terminal_and_wait(script)
                sys.exit(1)

            except Exception as inner_e:  # fallback to minimal error report
                if program_has_terminal:
                    print("[Error] Failed to handle crash: {}".format(inner_e))
                    print(traceback.format_exc())
                    input("Press Enter to exit.")
                else:
                    script = (
                        SCRIPT_BASE
                        + """
print("[Error] Failed to handle crash: " + {0!r})
print({1!r})
input("Press Enter to exit.")
""".format(str(inner_e), traceback.format_exc())
                    )
                    run_text_in_new_terminal_and_wait(script)

                sys.exit(1)

    # =============================

except Exception as e:
    import sys
    import traceback

    print("=" * 20)
    print("[Error] Failed in wrapper script with error: {}:".format(e))
    print("-" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("Press enter to exit")
    sys.exit(1)

finally:  # sys.exit(number) is not altered by this "finally" block
    try:
        log_file.close()  # type:ignore
    except Exception:
        pass
