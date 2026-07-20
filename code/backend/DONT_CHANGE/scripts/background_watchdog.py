"""WIP"""

# safe default (should be overwritten in following try block):
PROGRAM_HAS_TERMINAL = False  # means a new terminal will be created for prints

try:
    # ==============================
    # import Python packages
    # ==============================

    import atexit
    import ctypes
    import os
    import subprocess
    import sys
    import threading
    from ctypes import wintypes

    # ==============================
    # import third-party packages
    # ==============================

    # ==============================
    # imports from files
    # ==============================

    # add root dir to resolve file imports for debug cases where this script is called on its own:
    root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.developer_settings import (
        close_after_failure,
        close_after_KeyboardInterrupt,
        close_after_success,
        close_already_running_instances_on_start,
        enable_log_for_no_terminal_start,
        enable_log_for_Windows_terminal_start,
        input_prepend,
        log_input_prepend,
        log_path,
        log_path_is_relative_to_start_folder_if_relative,
        log_print_prepend,
        overwrite_log,
        prevent_start_if_already_running,
        print_prepend,
        program_name,
        prompt_to_close_existing_instances,
        start_in_shortcut_folder,
        use_global_python,
    )
    from backend.DONT_CHANGE.scripts._common_code import (
        close_terminal,
        get_running_processes_from_pid_file,
        make_empty_args_safe,
        resolve_log_path,
        set_terminal_colors,
        set_terminal_title,
        stop_processes_from_pid_file,
    )
    from backend.DONT_CHANGE.scripts._common_variables import (
        CORRECT_START_SIGNAL_FILE_PATH,
        EMPTY_ARG_INDICATOR,
        env_var_to_signal_startup_time_measurement,
        exit_processer_path,
        frontend_python_exe,
        frontend_script_wrapper_path,
        icon_path,
        process_id_file_path,
        python_script_path,
        start_time_dummy_main_script_path,
        tmp_traceback_json_path,
    )

    # ==============================
    # process imported variables
    # ==============================

    if log_print_prepend in (None, False, ""):
        log_print_prepend = ""
    if log_input_prepend in (None, False, ""):
        log_input_prepend = ""
    if print_prepend in (None, False, ""):
        print_prepend = ""
    if input_prepend in (None, False, ""):
        input_prepend = ""

    # ==============================
    # define local variables
    # ==============================

    KERNEL32_DLL = ctypes.WinDLL("kernel32", use_last_error=True)
    USER32_DLL = ctypes.WinDLL("user32", use_last_error=True)

    # ==============================
    # define local functions/classes
    # ==============================

    class _ProcessIdRegistry:
        """Maintain the PID file entries created by this launcher process."""

        def __init__(self, path: str) -> None:
            self.path = path
            self._process_ids: set[int] = set()
            self._lock = threading.RLock()

        def add(self, process_id: int) -> None:
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
                    pid_file.write(f"{process_id}\n")

        def remove(self, process_id: int) -> None:
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

        def cleanup(self) -> None:
            """Remove registered process IDs during interpreter shutdown."""
            for process_id in list(self._process_ids):
                self.remove(process_id)

    def get_candidate_hwnds() -> list[int]:
        candidate_hwnds: list[int] = []

        def add(hwnd: int) -> None:
            if hwnd == 0 or not USER32_DLL.IsWindow(hwnd) or hwnd in candidate_hwnds:
                return
            candidate_hwnds.append(hwnd)

        console_hwnd = int(KERNEL32_DLL.GetConsoleWindow() or 0)

        def get_console_title() -> str:
            buffer = ctypes.create_unicode_buffer(1024)
            title_length = KERNEL32_DLL.GetConsoleTitleW(buffer, len(buffer))
            if title_length == 0:
                return ""
            return buffer.value

        def get_root_owner(hwnd: int) -> int:
            GA_ROOTOWNER = 3
            if hwnd == 0:
                return 0
            return int(USER32_DLL.GetAncestor(hwnd, GA_ROOTOWNER) or 0)

        console_title = get_console_title()

        add(console_hwnd)
        add(get_root_owner(console_hwnd))

        if console_title:
            hwnd_by_console_class = int(USER32_DLL.FindWindowW("ConsoleWindowClass", console_title) or 0)
            add(hwnd_by_console_class)
            add(get_root_owner(hwnd_by_console_class))

            hwnd_by_title = int(USER32_DLL.FindWindowW(None, console_title) or 0)
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
            """WIP"""

            _fields_ = (
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8),
            )

        class PROPERTYKEY(ctypes.Structure):
            """WIP"""

            _fields_ = (("fmtid", GUID), ("pid", wintypes.DWORD))

        class PROPVARIANT(ctypes.Structure):
            """WIP"""

            _fields_ = (
                ("vt", ctypes.c_ushort),
                ("wReserved1", ctypes.c_ushort),
                ("wReserved2", ctypes.c_ushort),
                ("wReserved3", ctypes.c_ushort),
                ("pwszVal", ctypes.c_wchar_p),
            )

        class IPropertyStore(ctypes.Structure):
            """WIP"""

        IPropertyStorePtr = ctypes.POINTER(IPropertyStore)

        class IPropertyStoreVtbl(ctypes.Structure):
            """Describe the IPropertyStore COM vtable layout."""

            _fields_ = (
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
            )

        IPropertyStore._fields_ = [("lpVtbl", ctypes.POINTER(IPropertyStoreVtbl))]

        def make_guid(value: str) -> GUID:
            """WIP"""
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
            """WIP"""
            if hr < 0:
                message = f"{action} failed with HRESULT {format_hresult(hr)}"
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
            message = f"CoInitialize failed with HRESULT {format_hresult(coinitialize_result)}"
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

    def set_terminal_icon(candidate_hwnds: list[int], icon_path: str) -> None:
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

        signed_ptr = ctypes.c_ssize_t

        hinstance_type = wintypes.HINSTANCE
        wparam_type = wintypes.WPARAM
        lparam_type = wintypes.LPARAM
        lresult_type = signed_ptr

        KERNEL32_DLL.GetConsoleWindow.argtypes = []
        KERNEL32_DLL.GetConsoleWindow.restype = wintypes.HWND

        KERNEL32_DLL.GetConsoleTitleW.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
        KERNEL32_DLL.GetConsoleTitleW.restype = wintypes.DWORD

        KERNEL32_DLL.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        KERNEL32_DLL.OpenProcess.restype = wintypes.HANDLE

        KERNEL32_DLL.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        KERNEL32_DLL.QueryFullProcessImageNameW.restype = wintypes.BOOL

        KERNEL32_DLL.CloseHandle.argtypes = [wintypes.HANDLE]
        KERNEL32_DLL.CloseHandle.restype = wintypes.BOOL

        USER32_DLL.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        USER32_DLL.FindWindowW.restype = wintypes.HWND

        USER32_DLL.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        USER32_DLL.GetAncestor.restype = wintypes.HWND

        USER32_DLL.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        USER32_DLL.GetClassNameW.restype = ctypes.c_int

        USER32_DLL.GetSystemMetrics.argtypes = [ctypes.c_int]
        USER32_DLL.GetSystemMetrics.restype = ctypes.c_int

        USER32_DLL.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        USER32_DLL.GetWindowTextLengthW.restype = ctypes.c_int

        USER32_DLL.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        USER32_DLL.GetWindowTextW.restype = ctypes.c_int

        USER32_DLL.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        USER32_DLL.GetWindowThreadProcessId.restype = wintypes.DWORD

        USER32_DLL.IsWindow.argtypes = [wintypes.HWND]
        USER32_DLL.IsWindow.restype = wintypes.BOOL

        USER32_DLL.IsWindowVisible.argtypes = [wintypes.HWND]
        USER32_DLL.IsWindowVisible.restype = wintypes.BOOL

        USER32_DLL.LoadImageW.argtypes = [
            hinstance_type,
            wintypes.LPCWSTR,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        USER32_DLL.LoadImageW.restype = wintypes.HANDLE

        USER32_DLL.SendMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wparam_type,
            lparam_type,
        ]
        USER32_DLL.SendMessageW.restype = lresult_type

        if hasattr(USER32_DLL, "SetClassLongPtrW"):
            set_class_long = USER32_DLL.SetClassLongPtrW
            set_class_long.argtypes = [wintypes.HWND, ctypes.c_int, signed_ptr]
            set_class_long.restype = ctypes.c_size_t
        else:
            set_class_long = USER32_DLL.SetClassLongW
            set_class_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
            set_class_long.restype = wintypes.DWORD

        USER32_DLL.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        USER32_DLL.SetWindowPos.restype = wintypes.BOOL

        USER32_DLL.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        USER32_DLL.ShowWindow.restype = wintypes.BOOL

        def format_last_error(prefix: str) -> str:
            """Format the last error."""
            error_code = ctypes.get_last_error()
            if error_code == 0:
                return prefix
            return f"{prefix} ({error_code}: {ctypes.FormatError(error_code).strip()})"

        def get_window_text(hwnd: int) -> str:
            """Return the window text."""
            if hwnd == 0:
                return ""
            text_length = USER32_DLL.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(text_length + 1)
            USER32_DLL.GetWindowTextW(hwnd, buffer, len(buffer))
            return buffer.value

        def get_window_class_name(hwnd: int) -> str:
            if hwnd == 0:
                return ""
            buffer = ctypes.create_unicode_buffer(256)
            USER32_DLL.GetClassNameW(hwnd, buffer, len(buffer))
            return buffer.value

        def get_window_process_id(hwnd: int) -> int:
            if hwnd == 0:
                return 0
            process_id = wintypes.DWORD()
            USER32_DLL.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            return int(process_id.value)  # type: ignore

        def get_process_image_path(process_id: int) -> str:
            if process_id == 0:
                return ""

            process_handle = KERNEL32_DLL.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
            if not process_handle:
                return ""

            try:
                buffer_length = wintypes.DWORD(32768)
                buffer = ctypes.create_unicode_buffer(buffer_length.value)
                if KERNEL32_DLL.QueryFullProcessImageNameW(process_handle, 0, buffer, ctypes.byref(buffer_length)):
                    return buffer.value
                return ""
            finally:
                KERNEL32_DLL.CloseHandle(process_handle)

        def describe_window(hwnd: int) -> str:
            if hwnd == 0:
                return "hwnd=0x0"

            process_id = get_window_process_id(hwnd)
            return (
                f"hwnd=0x{hwnd:016X}, class={get_window_class_name(hwnd)!r}, "
                f"title={get_window_text(hwnd)!r}, visible={bool(USER32_DLL.IsWindowVisible(hwnd))}, "
                f"pid={process_id}, process={get_process_image_path(process_id)!r}"
            )

        def load_icon(path: str, width: int, height: int) -> int:
            icon_handle = USER32_DLL.LoadImageW(None, path, IMAGE_ICON, width, height, LR_LOADFROMFILE)
            if not icon_handle:
                icon_handle = USER32_DLL.LoadImageW(None, path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
            if not icon_handle:
                message = f'Failed to load icon from "{path}"'
                raise OSError(format_last_error(message))
            return int(icon_handle)

        def set_class_icon(hwnd: int, index: int, icon_handle: int) -> None:
            ctypes.set_last_error(0)
            set_class_long(hwnd, index, icon_handle)
            if ctypes.get_last_error() != 0:
                message = f"Failed to update window class icon for hwnd 0x{hwnd:016X}"
                raise OSError(format_last_error(message))

        normalized_icon_path = os.path.abspath(os.path.expanduser(icon_path))
        if not os.path.isfile(normalized_icon_path):
            message = f'Icon file not found: "{normalized_icon_path}"'
            raise FileNotFoundError(message)

        if not candidate_hwnds:
            raise RuntimeError("Could not find the current terminal window.")

        small_icon = load_icon(
            normalized_icon_path,
            USER32_DLL.GetSystemMetrics(SM_CXSMICON),
            USER32_DLL.GetSystemMetrics(SM_CYSMICON),
        )
        large_icon = load_icon(
            normalized_icon_path,
            USER32_DLL.GetSystemMetrics(SM_CXICON),
            USER32_DLL.GetSystemMetrics(SM_CYICON),
        )

        for hwnd in candidate_hwnds:
            USER32_DLL.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small_icon)
            USER32_DLL.SendMessageW(hwnd, WM_SETICON, ICON_BIG, large_icon)
            try:
                set_class_icon(hwnd, GCLP_HICONSM, small_icon)
                set_class_icon(hwnd, GCLP_HICON, large_icon)
            except OSError:
                pass
            _helper_refresh_nonclient_area(hwnd)

    def _helper_refresh_nonclient_area(hwnd: int) -> None:
        """WIP"""
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        USER32_DLL.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )

    def process_exit_here_or_in_new_terminal(
        exit_code: int | str,
        app_id: str,
        program_has_terminal: bool,
        log_path_resolved: str,
        selected_python_script_path: str,
    ):
        new_terminal_was_created = not program_has_terminal
        args = [
            str(exit_code),
            app_id,
            "true" if new_terminal_was_created else "false",
            log_path_resolved,
            selected_python_script_path,
        ]

        if not program_has_terminal:
            # don't wait:
            subprocess.Popen(  # noqa:S603
                [
                    "conhost.exe",
                    sys.executable,
                    "-X",
                    "faulthandler",
                    exit_processer_path,
                    *args,
                ],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )

        else:
            import runpy

            old_argv = sys.argv[:]
            try:
                sys.argv = ["_filename"] + args
                # waiting:
                runpy.run_path(exit_processer_path, run_name="__main__")
            finally:
                sys.argv = old_argv

    def get_frontend_args(selected_python_script_path: str, app_id: str, log_path: str) -> list[str]:
        """Get the arguments to pass to the frontend script."""

        return make_empty_args_safe(
            [
                EMPTY_ARG_INDICATOR,
                selected_python_script_path,
                app_id,
                print_prepend,
                input_prepend,
                log_input_prepend,
                log_path,
                "true" if overwrite_log else "false",
                log_print_prepend,
                tmp_traceback_json_path,
            ]
        )

    # ==============================
    # define main function
    # ==============================

    def main() -> None:
        global PROGRAM_HAS_TERMINAL

        # ==============================
        # tell the backend terminal via a signal file to close because successful start

        if CORRECT_START_SIGNAL_FILE_PATH:
            folder = os.path.dirname(CORRECT_START_SIGNAL_FILE_PATH)
            if folder:
                os.makedirs(folder, exist_ok=True)
            open(CORRECT_START_SIGNAL_FILE_PATH, "w", encoding="utf-8").close()

        # ==============================
        # delete old temporary crash traceback report if existing (to know if new one was created later)

        if os.path.exists(tmp_traceback_json_path):
            os.remove(tmp_traceback_json_path)

        # ==============================
        # get args

        _file_name, app_id, launch_mode = sys.argv
        if app_id == EMPTY_ARG_INDICATOR:
            app_id = ""

        # ==============================

        if launch_mode in ("wt", "conhost"):
            PROGRAM_HAS_TERMINAL = True

            set_terminal_colors()

            # set app-id for grouping of this terminal in taskbar with shorcut pinned to taskbar
            candidate_hwnds = get_candidate_hwnds()
            set_terminal_app_id_safe(candidate_hwnds, app_id)

            if launch_mode == "wt":
                set_terminal_icon(candidate_hwnds, icon_path)

            elif launch_mode == "conhost":
                # set terminal title in case shortcut was renamed:
                set_terminal_title(program_name)
        else:
            PROGRAM_HAS_TERMINAL = False

        # ==============================
        # add pid to "currently running" file:

        process_id_registry = _ProcessIdRegistry(process_id_file_path)
        process_id_registry.add(os.getpid())
        atexit.register(process_id_registry.cleanup)

        # ==============================
        # process args

        if use_global_python:
            python_exe_for_script = "py"
        else:
            python_exe_for_script = frontend_python_exe

        # ==============================
        # get log_path if logging is enabled

        if (launch_mode == "terminal" and enable_log_for_Windows_terminal_start) or (
            launch_mode == "no_terminal" and enable_log_for_no_terminal_start
        ):
            log_path_resolved = resolve_log_path(log_path, log_path_is_relative_to_start_folder_if_relative)
        else:
            log_path_resolved = ""

        # ==============================
        # close existing instances or block start if already running, if enabled

        if close_already_running_instances_on_start or prevent_start_if_already_running:
            running_process_ids, _stale_count = get_running_processes_from_pid_file(process_id_file_path)

            if close_already_running_instances_on_start:
                if running_process_ids:
                    stopped_count, _stale_count, failed_messages = stop_processes_from_pid_file(process_id_file_path)
                else:
                    stopped_count = 0
                    failed_messages = []
                if failed_messages:
                    raise RuntimeError("Failed to close existing program instance(s):\n" + "\n".join(failed_messages))
                if stopped_count:
                    print(f"[Info] Closed {stopped_count} existing program instance(s).")
            elif prevent_start_if_already_running:
                if running_process_ids:
                    print(
                        f"[Info] {len(running_process_ids)} existing program instance(s) are still running: "
                        + ", ".join(str(process_id) for process_id in running_process_ids)
                    )

                    if not prompt_to_close_existing_instances:
                        input("[Info] New launch cancelled. Press Enter to exit.")
                        sys.exit(0)

                    answer = input("Close the existing instance(s) and launch a new one? [y/N] ").strip().lower()
                    if answer not in {"y", "yes"}:
                        print("[Info] New launch cancelled.")
                        sys.exit(0)

                    stopped_count, _stale_count, failed_messages = stop_processes_from_pid_file(process_id_file_path)
                    if failed_messages:
                        raise RuntimeError(
                            "Failed to close existing program instance(s):\n" + "\n".join(failed_messages)
                        )
                    print(f"[Info] Closed {stopped_count} existing program instance(s).")

        # ==============================
        # setup variables used in launch

        if os.environ.get(env_var_to_signal_startup_time_measurement):
            selected_python_script_path = start_time_dummy_main_script_path
            os.environ.pop(env_var_to_signal_startup_time_measurement, None)
        else:
            selected_python_script_path = python_script_path

        if not os.path.exists(selected_python_script_path):
            raise FileNotFoundError(f'[Error] Python script not found at "{selected_python_script_path}"')

        passed_args = get_frontend_args(selected_python_script_path, app_id, log_path_resolved)

        if start_in_shortcut_folder:
            wdir_is_script_dir = False
            cwd_for_main_script = None
        else:
            wdir_is_script_dir = True
            cwd_for_main_script = os.path.dirname(selected_python_script_path)

        # ==============================
        # set environment variables for main.py script

        wrapper_env_vars = os.environ.copy()
        wrapper_env_vars["PROGRAM_NAME"] = program_name
        wrapper_env_vars["ICON_PATH"] = icon_path
        wrapper_env_vars["LOG_PATH"] = log_path_resolved
        wrapper_env_vars["APP_ID"] = app_id
        wrapper_env_vars["PROGRAM_HAS_TERMINAL"] = "1" if PROGRAM_HAS_TERMINAL else "0"
        wrapper_env_vars["WDIR_IS_SCRIPT_DIR"] = "1" if wdir_is_script_dir else "0"
        wrapper_env_vars["CLOSE_AFTER_FAILURE"] = "1" if close_after_failure else "0"
        wrapper_env_vars["CLOSE_AFTER_SUCCESS"] = "1" if close_after_success else "0"
        wrapper_env_vars["CLOSE_AFTER_KEYBOARDINTERRUPT"] = "1" if close_after_KeyboardInterrupt else "0"

        # ==============================
        # start wrapper script and don't wait for finish

        process = subprocess.Popen(  # noqa:S603
            [python_exe_for_script, frontend_script_wrapper_path, *passed_args],
            encoding="utf-8",
            env=wrapper_env_vars,
            cwd=cwd_for_main_script,
        )

        # ==============================
        # update terminal appearance if visible

        if PROGRAM_HAS_TERMINAL:
            # set terminal icon + app-ID (for taskabr grouping of terminal) in new thread because slow:
            def _set_terminal_icon_and_app_id() -> None:
                try:
                    candidate_hwnds = get_candidate_hwnds()
                    set_terminal_icon(candidate_hwnds, icon_path)  # type: ignore
                    set_terminal_app_id_safe(candidate_hwnds, app_id)  # type: ignore
                except Exception as error:
                    print(f"[Warning] Error during terminal appearance update: {error}")

            terminal_appearance_thread = threading.Thread(target=_set_terminal_icon_and_app_id)
            terminal_appearance_thread.start()
        else:
            terminal_appearance_thread = None

        # ==============================
        # wait for finish of wrapper

        # Ctrl+C is delivered to every process attached to this console.
        # Ignore it in the watchdog while waiting so main.py receives the first interrupt.
        import signal

        old_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            process.wait()
        finally:
            signal.signal(signal.SIGINT, old_sigint_handler)

        # ==============================
        # handle exit of wrapper

        exit_mode = process.returncode # Can be 0,1,2,3
        
        # exit_mode meaning:
        # 0 = correctly handled end of script in main.py (no json)
        # 1 = correctly handled other exit of main.py (json)
        # 2 = handled failure in wrapper of main.py (json)
        # 3 = unsuccessfully handled failure in wrapper of main.py (no json)
        # (4 = handled failure in this script. See Exception of main below)

        # process exit in current terminal if it exists or in new terminal if not. Wait in the second case:
        process_exit_here_or_in_new_terminal(
            exit_mode, app_id, PROGRAM_HAS_TERMINAL, log_path_resolved, selected_python_script_path
        )

    # ==============================
    # execute main function
    # ==============================

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            # WIP_ save_exception_as_json()
            process_exit_here_or_in_new_terminal(
                exit_code=4,
                app_id="",
                program_has_terminal=PROGRAM_HAS_TERMINAL,
                log_path_resolved="",
                selected_python_script_path="",
            )

        close_terminal()

    # ==============================

except Exception as e:
    import os
    import traceback

    # WIP: assume no terminal and make new windwo and print traceback

    PROGRAM_HAS_TERMINAL

    print()
    print()
    print("=" * 30)
    print(f"[Error] Within background watchdog: {e}")
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    input("[Error] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
