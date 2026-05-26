try:
    # ==================
    # import

    import atexit
    import builtins
    import faulthandler
    import os
    import re
    import runpy
    import sys

    # ==================
    # add root dir for imports:

    root_dir = os.path.dirname(__file__) + "\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # ==================
    # import common code

    from developer_settings import (
        close_on_crash,
        close_on_failure,
        close_on_success,
        open_log_file_after_crash,
        open_log_file_after_failure,
        open_log_file_after_success,
        overwrite_log,
        program_name,
        send_Windows_notification_on_crash,
        send_Windows_notification_on_failure,
        send_Windows_notification_on_success,
        start_minimized,
        # taskbar_flashing_on_crash,
        # taskbar_flashing_on_failure,
        # taskbar_flashing_on_success,
        # taskbar_highlight_on_crash,
        # taskbar_highlight_on_failure,
        # taskbar_highlight_on_success,
    )
    from DONT_CHANGE.specific_scripts.common_variables import EMPTY_ARG_INDICATOR, icon_path
    from DONT_CHANGE.specific_scripts.get_launcher_settings import (
        CompletionAlerts,
        input_prepend,
        log_input_prepend,
        log_print_prepend,
        looks_like_interpreter_crash,
        play_sound_on_crash,
        play_sound_on_failure,
        play_sound_on_success,
        print_prepend,
        python_script_path,
        wdir_is_script_dir,
    )

    # ==================
    # import args

    def arg_to_str(idx, default="") -> str:
        arg = sys.argv[idx]
        if arg == EMPTY_ARG_INDICATOR:
            return default
        else:
            return arg

    app_id = arg_to_str(1)
    log_path = arg_to_str(2)
    terminal_colors = arg_to_str(3)
    windows_terminal_mode = arg_to_str(4)
    if windows_terminal_mode not in {"classic", "modern", "invisible"}:
        raise ValueError(
            f'[Error] Unknown windows_terminal_mode "{windows_terminal_mode}". '
            "Expected one of: classic, modern, invisible"
        )
    classic_terminal_cols = arg_to_str(5)
    classic_terminal_lines = arg_to_str(6)

    # ==================
    # process args

    program_has_terminal = windows_terminal_mode != "invisible"

    # WIP???
    completion_alerts = CompletionAlerts(
        title=program_name,
        app_id=app_id,
        log_path=log_path,
        play_sound_on_success=play_sound_on_success,
        send_windows_notification_on_success=send_Windows_notification_on_success,
        play_sound_on_failure=play_sound_on_failure,
        send_windows_notification_on_failure=send_Windows_notification_on_failure,
        play_sound_on_python_interpreter_crash=play_sound_on_crash,
        send_windows_notification_on_python_interpreter_crash=send_Windows_notification_on_crash,
        open_log_file_after_success=open_log_file_after_success,
        open_log_file_after_failure=open_log_file_after_failure,
        open_log_file_after_python_interpreter_crash=open_log_file_after_crash,
    )

    # ==================
    # define functions and variables

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

    def strip_ansi_escape_sequences(text: str) -> str:
        return ANSI_ESCAPE_RE.sub("", text)

    def print_warn(msg, sep: str | None = " ", end: str | None = "\n"):
        print(f"{ANSI_WARN}{msg}{ANSI_RESET}", sep=sep, end=end)

    def input_warn(msg):
        return input(f"{ANSI_WARN}{msg}{ANSI_RESET}")

    def input_success(msg):
        return input(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}")

    def run_text_in_new_terminal_and_wait(text):
        import subprocess
        import sys

        subprocess.run(  # noqa:S603
            [sys.executable, "-X", "faulthandler", "-c", text], creationflags=subprocess.CREATE_NEW_CONSOLE
        )

    # import time
    # time1 = time.time()
    # takes 11 ms on python 3.14
    if program_has_terminal:
        import ctypes
        from ctypes import wintypes

        kernel32_DLL = ctypes.WinDLL("kernel32", use_last_error=True)  # type:ignore
        user32_DLL = ctypes.WinDLL("user32", use_last_error=True)

        def _helper_refresh_nonclient_area(hwnd: int) -> None:
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

        def minimize_current_console() -> None:
            try:
                hwnd = kernel32_DLL.GetConsoleWindow()
                if hwnd:
                    user32_DLL.ShowWindow(hwnd, 2)
            except Exception:
                pass

        def get_candidate_hwnds() -> list[int]:
            candidate_hwnds: list[int] = []

            def add(hwnd: int) -> None:
                if hwnd == 0 or not user32_DLL.IsWindow(hwnd) or hwnd in candidate_hwnds:
                    return
                candidate_hwnds.append(hwnd)

            console_hwnd = int(kernel32_DLL.GetConsoleWindow() or 0)

            def get_console_title() -> str:
                buffer = ctypes.create_unicode_buffer(1024)
                title_length = kernel32_DLL.GetConsoleTitleW(buffer, len(buffer))
                if title_length == 0:
                    return ""
                return buffer.value

            def get_root_owner(hwnd: int) -> int:
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

        def set_terminal_app_id_safe(candidate_hwnds: list[int], app_id: str) -> int:
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
                _fields_ = [
                    ("Data1", ctypes.c_ulong),
                    ("Data2", ctypes.c_ushort),
                    ("Data3", ctypes.c_ushort),
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

            IPropertyStorePtr = ctypes.POINTER(IPropertyStore)

            class IPropertyStoreVtbl(ctypes.Structure):
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

            def make_guid(value: str) -> GUID:
                parsed = uuid.UUID(value)
                return GUID(
                    parsed.time_low,
                    parsed.time_mid,
                    parsed.time_hi_version,
                    (ctypes.c_ubyte * 8)(*parsed.bytes[8:]),
                )

            def format_hresult(hr: int) -> str:
                code = hr & 0xFFFFFFFF
                try:
                    message = ctypes.FormatError(code).strip()
                except Exception:
                    message = "unknown error"
                return f"0x{code:08X}: {message}"

            def check_hresult(hr: int, action: str) -> None:
                if hr < 0:
                    raise OSError(f"{action} failed with HRESULT {format_hresult(hr)}")

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
                raise OSError(f"CoInitialize failed with HRESULT {format_hresult(coinitialize_result)}")

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
                        check_hresult(hr, f"SHGetPropertyStoreForWindow for hwnd 0x{hwnd:016X}")

                        try:
                            hr = property_store.contents.lpVtbl.contents.SetValue(
                                property_store,
                                ctypes.byref(pkey_app_user_model_id),
                                ctypes.byref(prop_var),
                            )
                            check_hresult(hr, f"SetValue System.AppUserModel.ID for hwnd 0x{hwnd:016X}")

                            hr = property_store.contents.lpVtbl.contents.Commit(property_store)
                            check_hresult(hr, f"Commit System.AppUserModel.ID for hwnd 0x{hwnd:016X}")

                            _helper_refresh_nonclient_area(hwnd)
                            changed_count += 1
                        finally:
                            if property_store:
                                property_store.contents.lpVtbl.contents.Release(property_store)
                    except Exception as error:
                        print(f"[Info] AppID update skipped for hwnd 0x{hwnd:016X}: {error}")
            finally:
                if should_uninitialize:
                    ole32.CoUninitialize()

            return changed_count

        def set_terminal_icon(candidate_hwnds, icon_path: str):
            """Change the icon of the current terminal window"""

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

            def format_last_error(prefix: str) -> str:
                error_code = ctypes.get_last_error()
                if error_code == 0:
                    return prefix
                return f"{prefix} ({error_code}: {ctypes.FormatError(error_code).strip()})"

            def get_window_text(hwnd: int) -> str:
                if hwnd == 0:
                    return ""
                text_length = user32_DLL.GetWindowTextLengthW(hwnd)
                buffer = ctypes.create_unicode_buffer(text_length + 1)
                user32_DLL.GetWindowTextW(hwnd, buffer, len(buffer))
                return buffer.value

            def get_window_class_name(hwnd: int) -> str:
                if hwnd == 0:
                    return ""
                buffer = ctypes.create_unicode_buffer(256)
                user32_DLL.GetClassNameW(hwnd, buffer, len(buffer))
                return buffer.value

            def get_window_process_id(hwnd: int) -> int:
                if hwnd == 0:
                    return 0
                process_id = wintypes.DWORD()
                user32_DLL.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
                return int(process_id.value)  # type:ignore

            def get_process_image_path(process_id: int) -> str:
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

            def describe_window(hwnd: int) -> str:
                if hwnd == 0:
                    return "hwnd=0x0"

                process_id = get_window_process_id(hwnd)
                return (
                    f"hwnd=0x{hwnd:016X}, "
                    f"class={get_window_class_name(hwnd)!r}, "
                    f"title={get_window_text(hwnd)!r}, "
                    f"visible={bool(user32_DLL.IsWindowVisible(hwnd))}, "
                    f"pid={process_id}, "
                    f"process={get_process_image_path(process_id)!r}"
                )

            def load_icon(path: str, width: int, height: int) -> int:
                icon_handle = user32_DLL.LoadImageW(None, path, IMAGE_ICON, width, height, LR_LOADFROMFILE)
                if not icon_handle:
                    icon_handle = user32_DLL.LoadImageW(None, path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
                if not icon_handle:
                    raise OSError(format_last_error(f'Failed to load icon from "{path}"'))
                return int(icon_handle)

            def set_class_icon(hwnd: int, index: int, icon_handle: int) -> None:
                ctypes.set_last_error(0)
                set_class_long(hwnd, index, icon_handle)
                if ctypes.get_last_error() != 0:
                    raise OSError(format_last_error(f"Failed to update window class icon for hwnd 0x{hwnd:016X}"))

            normalized_icon_path = os.path.abspath(os.path.expanduser(icon_path))
            if not os.path.isfile(normalized_icon_path):
                raise FileNotFoundError(f'Icon file not found: "{normalized_icon_path}"')

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

    # time2 = time.time()
    # print(time2 - time1)

    # end of "if script_has_terminal:""
    # ==================================

    # define code to log prints and errors
    if log_path != "":
        import threading
        from datetime import datetime, timezone

        def prepare_log_path(path: str) -> str:
            path = datetime.now(timezone.utc).strftime(path)
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)

            return path

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
                print_timestamp_format: str | None = "[%H:%M:%S] ",
                log_timestamp_format: str | None = "[%H:%M:%S]\t",
                input_timestamp_format: str | None = "",
                log_input_timestamp_format: str | None = "",
                print_red: bool = False,
                auto_flush: bool = True,
            ) -> None:
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

            def _timestamp_prefix(self, fmt: str | None) -> str:
                if not fmt:
                    return ""
                return datetime.now(timezone.utc).strftime(fmt)

            def _print_supports_color(self) -> bool:
                return bool(getattr(self.print_stream, "isatty", lambda: False)())

            def write(self, data: str) -> int:
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

            def write_input_prompt(self, prompt: str) -> None:
                if prompt is None:
                    prompt = ""
                if not isinstance(prompt, str):
                    prompt = str(prompt)

                with self._lock:
                    print_prefix = self._timestamp_prefix(self.input_timestamp_format)
                    log_prefix = self._timestamp_prefix(self.log_input_timestamp_format)

                    self.print_stream.write(f"{print_prefix}{prompt}")
                    if self.log_stream is not None:
                        self.log_stream.write(f"{log_prefix}{strip_ansi_escape_sequences(prompt)}")

                    self._at_line_start = prompt.endswith("\n")
                    if self.auto_flush:
                        self.flush()

            def complete_input_line(self, text: str) -> None:
                with self._lock:
                    if self.log_stream is not None and not self._at_line_start:
                        self.log_stream.write(f"{text}\n")
                    self._at_line_start = True
                    if self.auto_flush:
                        self.flush()

            def flush(self) -> None:
                with self._lock:
                    if hasattr(self.print_stream, "flush"):
                        self.print_stream.flush()
                    if self.log_stream is not None and hasattr(self.log_stream, "flush"):
                        self.log_stream.flush()

            def isatty(self) -> bool:
                return bool(getattr(self.print_stream, "isatty", lambda: False)())

            def writable(self) -> bool:
                return True

            def fileno(self) -> int:
                if hasattr(self.print_stream, "fileno"):
                    return self.print_stream.fileno()
                raise OSError("Underlying print_stream does not support fileno()")

            @property
            def encoding(self) -> str | None:
                return getattr(self.print_stream, "encoding", None)

        def setup_log_prints(log_path, overwrite_log=True):
            global log_file  # type:ignore
            log_path = prepare_log_path(log_path)
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

    # end of "if log_path != "":"
    # ==================================

    # used to print in new terminal window:
    script_base = r"""
import os

ANSI_RESET = "\033[0m"
ANSI_WARN = "\x1b[1;37;41m"
ANSI_SUCCESS = "\x1b[1;37;42m"

def print_warn(msg, sep: str | None = " ", end: str | None = "\n"):
    print(f"{ANSI_WARN}{msg}{ANSI_RESET}", sep=sep, end=end)

def input_warn(msg):
    return input(f"{ANSI_WARN}{msg}{ANSI_RESET}")

def input_success(msg):
    return input(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}")

def set_terminal_name(name: str) -> None:
    try:
        os.system(f"title {name.replace('r\n', '').replace(r'\r', '')}")
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

    # ==================
    # execute
    # ==================

    try:
        # minimize terminal if wanted
        if program_has_terminal and start_minimized:
            minimize_current_console()  # type:ignore

        # set terminal colors
        if program_has_terminal and terminal_colors != "":
            os.system(f"color {terminal_colors}")  # noqa:S605
        if windows_terminal_mode == "classic" and (classic_terminal_cols != "" or classic_terminal_lines != ""):
            mode_parts = []
            if classic_terminal_cols != "":
                mode_parts.append(f"cols={classic_terminal_cols}")
            if classic_terminal_lines != "":
                mode_parts.append(f"lines={classic_terminal_lines}")
            os.system("mode con: " + " ".join(mode_parts))  # noqa:S605

        # set terminal name
        if program_name != "":
            os.system(f"title {program_name}")  # noqa:S605

        # needed if main script spawns a GUI: For taskbar grouping (combining) of launched window with shortcut icon
        if app_id != "":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)  # type:ignore
            except Exception as e:
                print(f"[Info] Failed to set app id for taskbar grouping: {e}")

        # set terminal appearance in new thread because slow: terminal title+icon+appID (for taskabr grouping)
        # import time
        # time1 = time.time()
        terminal_appearance_thread = None
        if program_has_terminal:

            def apply_terminal_appearance() -> None:
                try:
                    candidate_hwnds = get_candidate_hwnds()
                    set_terminal_icon(candidate_hwnds, icon_path)  # type:ignore
                    set_terminal_app_id_safe(candidate_hwnds, app_id)  # type:ignore

                except Exception as error:
                    print(f"[Error] Terminal appearance update skipped: {error}")

            import threading

            terminal_appearance_thread = threading.Thread(target=apply_terminal_appearance)
            terminal_appearance_thread.start()
        # time2 = time.time()
        # print(time2 - time1)

        # set working directory
        if wdir_is_script_dir:
            os.chdir(os.path.dirname(python_script_path))

        # setup logging
        if log_path != "":
            setup_log_prints(log_path, overwrite_log)  # type:ignore

        # change pythons builtin "input" function
        original_input = builtins.input
        if input_prepend != "" or log_input_prepend != "" or hasattr(sys.stdout, "complete_input_line"):

            def input_with_prepend(prompt=""):
                if hasattr(sys.stdout, "write_input_prompt"):
                    sys.stdout.write_input_prompt(prompt)
                    text = original_input("")
                else:
                    text = original_input(f"{input_prepend}{prompt}")
                if hasattr(sys.stdout, "complete_input_line"):
                    sys.stdout.complete_input_line(text)
                return text

            builtins.input = input_with_prepend

        # define environemental variables to pass to main script
        os.environ["PROGRAM_NAME"] = program_name
        os.environ["ICON_PATH"] = icon_path
        os.environ["LOG_PATH"] = log_path
        os.environ["APP_ID"] = app_id
        os.environ["PROGRAM_HAS_TERMINAL"] = "1" if program_has_terminal else "0"
        os.environ["WDIR_IS_SCRIPT_DIR"] = "1" if wdir_is_script_dir else "0"
        os.environ["CLOSE_ON_FAILURE"] = "1" if close_on_failure else "0"
        os.environ["CLOSE_ON_SUCCESS"] = "1" if close_on_success else "0"

        # change sys.path[0] to be dir of target script and not this script
        sys.path[0] = os.path.dirname(python_script_path)

        # run in the current python process and wait for finish
        try:
            runpy.run_path(python_script_path, run_name="__main__")
            exit_code = 0  # meaning no crash
        except SystemExit as e:  # catches sys.exit
            exit_code = e.code
            if exit_code is None:
                exit_code = 0
        except SyntaxError as e:  # catches synatx error in script_path or raise by script_path
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

        # change terminal and print depending on exit_code
        if exit_code == 0:
            completion_alerts.run("success", exit_code)
            if close_on_success:
                sys.exit(0)
            else:
                script = (
                    script_base
                    + """
set_terminal_name(rf"[Success] {{get_terminal_name()}}")
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
            completion_alerts.run("crash", exit_code)
            if close_on_crash:
                sys.exit(exit_code)
            else:
                script = (
                    script_base
                    + f"""
set_terminal_name(rf"[Crash] {{get_terminal_name()}}")
print()
print_warn(rf'[Python Interpreter Crash] Script exited with Windows crash code: "{exit_code}"')
input_warn("[Python Interpreter Crash] Press Enter to exit.")
"""
                )
                if program_has_terminal:
                    exec(script)  # noqa
                else:
                    run_text_in_new_terminal_and_wait(script)
                sys.exit(exit_code)

        else:  # regular failure case (includes any string exit_code)
            completion_alerts.run("failure", exit_code)
            if close_on_failure:
                sys.exit(exit_code)
            else:
                script = (
                    script_base
                    + f"""
set_terminal_name(rf"[Failure] {{get_terminal_name()}}")
print()
print_warn(rf"[Python Failure Return] Script exited with code: {exit_code}")
input_warn("[Python Failure Return] Press Enter to exit.")
"""
                )
                if program_has_terminal:
                    exec(script)  # noqa
                else:
                    run_text_in_new_terminal_and_wait(script)

                sys.exit(exit_code)

    except Exception as e:  # backend crash
        import sys
        import traceback

        try:  # attempt detailed error report
            script = (
                script_base
                + f"""
set_terminal_name(rf"[Crash] {{get_terminal_name()}}")
print()
print_warn("="*40)
print_warn(r"CRITICAL LAUNCH ERROR: {e}")
print_warn("-"*40)
print_warn(r\"""{traceback.format_exc()}\""",end="")
print_warn("-"*40)
print_warn(r"[Info] Python Exe: {sys.executable}")
print_warn(r"[Info] Script: {python_script_path}")
print_warn("-"*40)
input_warn("[Python Crash] See above. Press Enter to exit.")
"""
            )
            if program_has_terminal:
                exec(script)  # noqa
            else:
                run_text_in_new_terminal_and_wait(script)
            sys.exit(1)

        except Exception as inner_e:  # fallback to minimal error report
            if program_has_terminal:
                print(f"[Error] Failed to handle crash: {inner_e}")
                print({traceback.format_exc()})
                input("Press Enter to exit.")
            else:
                script = (
                    script_base
                    + f"""
                print(f"[Error] Failed to handle crash: {inner_e}")
                print({traceback.format_exc()})
                input("Press Enter to exit.")
                """
                )
                run_text_in_new_terminal_and_wait(script)

            sys.exit(1)


except Exception as e:
    import sys
    import traceback

    print("=" * 20)
    print(f"[Error] Failed in wrapper script with error: {e}:")
    print("-" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("Press enter to exit")
    sys.exit(1)

finally:
    try:
        log_file.close()  # type:ignore
    except Exception:
        pass
    # sys.exit(number) is not altered by this "finally" block
