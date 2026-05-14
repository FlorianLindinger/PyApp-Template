import os
import subprocess
import sys

# add root dir for debug cases where this script is called on its own:
root_dir = os.path.dirname(__file__) + "\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from developer_settings import install_tests, install_tkinter, install_tools, program_name, python_version
from DONT_CHANGE.specific_scripts.common_variables import (
    default_packages_file_path,
    determined_current_packages_file_path_noVersion,
    determined_current_packages_file_path_withVersion,
    determined_needed_packages_output_file_path_noVersion,
    determined_needed_packages_output_file_path_withVersion,
    excluded_folders_for_package_search,
    icon_path,
    portable_python_installer_path,
    portable_venv_creator_path,
    py_env_dir,
    python_dist_path,
    python_exe_path,
    python_scripts_dir,
    python_version_indicator_file_path,
    rel_path_py_env_to_python_dist,
    variable_in_default_packages_path_that_triggers_search_if_true,
    venv_dir_path,
    venv_exe_path,
)

# =========================
# global variables

_ICON_WAS_SET = False
_APP_ID_IS_SET = False

ANSI_WARN = "\x1b[1;37;41m"  # white text, red bg, bold
ANSI_SUCCESS = "\x1b[1;37;42m"  # white text, green bg, bold
ANSI_RESET = "\033[0m"

# =========================
# colored print and input and general print related


def print_warn(msg, sep: str | None = " ", end: str | None = "\n"):
    print(f"{ANSI_WARN}{msg}{ANSI_RESET}", sep=sep, end=end)


def input_warn(msg):
    return input(f"{ANSI_WARN}{msg}{ANSI_RESET}")


def input_success(msg):
    return input(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}")


def print_traceback(message="Error", add_press_enter_to_exit=False) -> None:
    """colored traceback via "rich" package"""

    exc_type, exc_value, tb = sys.exc_info()
    try:
        import rich.box
        import rich.console
        import rich.panel
        import rich.text
        import rich.traceback

        if exc_type is None or exc_value is None:
            rich.console.Console().print(
                "[yellow][Warning] Running print_traceback function without active exception.[/yellow]"
            )
            if add_press_enter_to_exit:
                rich.console.Console().print("[red]Press enter to exit[/red]")
        else:
            panel = rich.panel.Panel(
                rich.traceback.Traceback.from_exception(
                    exc_type,
                    exc_value,
                    tb,
                    show_locals=False,
                ),
                title=rich.text.Text(message, style="bold red on white"),
                title_align="left",
                subtitle=rich.text.Text("Press Enter to exit", style="bold red on white")
                if add_press_enter_to_exit
                else None,
                subtitle_align="left",
                box=rich.box.HEAVY,
                border_style="bold red",
                padding=(1, 2),
                expand=False,
            )
            rich.console.Console().print(panel)

    # fallback
    except Exception:
        import traceback

        print(traceback.print_exception(exc_type, exc_value, tb))

    # close and potetniall prompt before
    finally:
        if add_press_enter_to_exit:
            input()
        close_terminal()
        sys.exit(1)  # should not be reached after close_terminal()


# =========================
# miscellaneous


def delete_folder_safe(
    target: str | os.PathLike[str],
    *,
    prompt_message="Delete this folder? [y/n]: ",
    allowed_base: str | os.PathLike[str],
    expected_name: str | None = None,
    prompt_for_confirmation=True,
) -> bool:
    import shutil  # lazy import because takes 0.2 s

    target_path = os.path.realpath(os.path.abspath(os.fspath(target)))
    base_path = os.path.realpath(os.path.abspath(os.fspath(allowed_base)))

    if not os.path.exists(target_path):
        return False

    if expected_name is not None and os.path.basename(target_path).lower() != expected_name.lower():
        raise RuntimeError(f'Refusing to delete "{target_path}" because its folder name is not "{expected_name}".')

    if not os.path.exists(base_path):
        raise FileNotFoundError(f"Allowed base does not exist: {base_path}")

    if not os.path.isdir(base_path):
        raise NotADirectoryError(f"Allowed base is not a directory: {base_path}")

    if not os.path.isdir(target_path):
        raise NotADirectoryError(f"Target is not a directory: {target_path}")

    # check if file system root
    if os.path.abspath(target_path) == os.path.abspath(os.path.join(target_path, os.pardir)):
        raise ValueError(f"Refusing to delete filesystem root: {target_path}")

    if os.path.normcase(target_path) == os.path.normcase(base_path):
        raise ValueError("Refusing to delete the allowed base directory itself")

    try:
        common_path = os.path.commonpath([base_path, target_path])
    except ValueError as exc:
        raise ValueError(
            f"Refusing to delete directory outside allowed base.\nTarget: {target_path}\nAllowed base: {base_path}"
        ) from exc

    if os.path.normcase(common_path) != os.path.normcase(base_path):
        raise ValueError(
            f"Refusing to delete directory outside allowed base.\nTarget: {target_path}\nAllowed base: {base_path}"
        )

    if prompt_for_confirmation:
        print()
        print("Folder deletion request:")
        print(f"Folder: {target_path}")
        print(f"Folder size: {_format_bytes(_get_folder_size(target_path))}")
        print()
        answer = input(prompt_message).strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled folder deletion.")
            return False

    print(f'[Info] Deleting "{target_path}"')
    shutil.rmtree(target_path)
    if os.path.exists(target_path):
        raise RuntimeError(f'Failed to delete "{target_path}"')
    return True


# =========================
# terminal related


def set_terminal_app_id_safe(app_id: str) -> int:
    """Try to set System.AppUserModel.ID on the terminal window itself."""
    import ctypes
    from ctypes import wintypes

    candidate_hwnds = _get_candidate_hwnds()

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


def set_terminal_icon(window_title: str, icon_path: str) -> int:
    """Best-effort update of the current Windows terminal icon using ctypes only."""
    if icon_path == "":
        return 0

    normalized_icon_path = os.path.abspath(os.path.expanduser(icon_path))
    if not os.path.isfile(normalized_icon_path):
        return 0

    try:
        import ctypes
        import time
        import uuid
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        kernel32.GetConsoleWindow.restype = wintypes.HWND
        kernel32.GetConsoleTitleW.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
        kernel32.GetConsoleTitleW.restype = wintypes.DWORD
        kernel32.SetConsoleTitleW.argtypes = [wintypes.LPCWSTR]
        kernel32.SetConsoleTitleW.restype = wintypes.BOOL

        user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        user32.FindWindowW.restype = wintypes.HWND
        lparam_type = getattr(wintypes, "LPARAM", ctypes.c_ssize_t)
        enum_windows_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, lparam_type)
        user32.EnumWindows.argtypes = [enum_windows_proc, lparam_type]
        user32.EnumWindows.restype = wintypes.BOOL
        user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
        user32.GetAncestor.restype = wintypes.HWND
        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindow.restype = wintypes.BOOL
        user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.SendMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
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
        GA_ROOTOWNER = 3
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        def get_console_title() -> str:
            buffer = ctypes.create_unicode_buffer(1024)
            title_length = kernel32.GetConsoleTitleW(buffer, len(buffer))
            return buffer.value if title_length else ""

        original_title = get_console_title()
        final_title = window_title or original_title
        marker_title = f"PyAppTemplate-{os.getpid()}-{uuid.uuid4().hex}"

        def add_candidate(candidates: list[int], hwnd: int) -> None:
            if hwnd and user32.IsWindow(hwnd) and hwnd not in candidates:
                candidates.append(int(hwnd))  # type:ignore

        def add_with_root(candidates: list[int], hwnd: int) -> None:
            add_candidate(candidates, hwnd)
            if hwnd:
                add_candidate(candidates, int(user32.GetAncestor(hwnd, GA_ROOTOWNER) or 0))

        def get_window_text(hwnd: int) -> str:
            text_length = user32.GetWindowTextLengthW(hwnd)
            if text_length <= 0:
                return ""
            buffer = ctypes.create_unicode_buffer(text_length + 1)
            user32.GetWindowTextW(hwnd, buffer, len(buffer))
            return buffer.value

        def find_windows_by_exact_title(title: str) -> list[int]:
            matching_hwnds: list[int] = []
            if title == "":
                return matching_hwnds

            hwnd = int(user32.FindWindowW("ConsoleWindowClass", title) or 0)
            add_with_root(matching_hwnds, hwnd)
            hwnd = int(user32.FindWindowW(None, title) or 0)
            add_with_root(matching_hwnds, hwnd)
            return matching_hwnds

        def find_windows_by_title_fragment(title: str) -> list[int]:
            matching_hwnds: list[int] = []
            if title == "":
                return matching_hwnds

            def enum_proc(hwnd: int, _lparam: int) -> bool:
                try:
                    if title in get_window_text(hwnd):
                        add_with_root(matching_hwnds, int(hwnd))  # type:ignore
                except Exception:
                    pass
                return True

            callback = enum_windows_proc(enum_proc)
            user32.EnumWindows(callback, 0)
            return matching_hwnds

        candidates: list[int] = []
        console_hwnd = int(kernel32.GetConsoleWindow() or 0)
        add_with_root(candidates, console_hwnd)

        try:
            kernel32.SetConsoleTitleW(marker_title)
            time.sleep(0.05)
            for hwnd in find_windows_by_exact_title(marker_title):
                add_with_root(candidates, hwnd)
            for hwnd in find_windows_by_title_fragment(marker_title):
                add_with_root(candidates, hwnd)
        finally:
            kernel32.SetConsoleTitleW(final_title)

        def load_icon(width: int, height: int) -> int:
            icon = user32.LoadImageW(None, normalized_icon_path, IMAGE_ICON, width, height, LR_LOADFROMFILE)
            if not icon:
                icon = user32.LoadImageW(None, normalized_icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
            return int(icon or 0)

        small_icon = load_icon(
            user32.GetSystemMetrics(SM_CXSMICON),
            user32.GetSystemMetrics(SM_CYSMICON),
        )
        large_icon = load_icon(
            user32.GetSystemMetrics(SM_CXICON),
            user32.GetSystemMetrics(SM_CYICON),
        )
        if small_icon == 0 and large_icon == 0:
            return 0

        changed_count = 0
        for hwnd in candidates:
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
            changed_count += 1

        return changed_count
    except Exception:
        return 0


def set_terminal_name(name: str) -> None:
    try:
        clean_name = name.replace("\r\n", "").replace("\r", "")
        os.system(f"title {clean_name}")  # noqa:S605
    except Exception:
        pass


def set_terminal_icon_once():
    global _ICON_WAS_SET
    if _ICON_WAS_SET == False:
        set_terminal_name(program_name)
        set_terminal_icon(program_name, icon_path)
        _ICON_WAS_SET = True


def set_app_id_once(app_id: str):
    global _APP_ID_IS_SET
    if _APP_ID_IS_SET == False:
        set_terminal_app_id_safe(app_id)
        _APP_ID_IS_SET = True


def close_terminal() -> bool:
    parent_pid = os.getppid()
    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, parent_pid)
        if not process_handle:
            parent_image_path = ""
        try:
            buffer_length = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(buffer_length.value)
            if not kernel32.QueryFullProcessImageNameW(process_handle, 0, buffer, ctypes.byref(buffer_length)):
                parent_image_path = ""
            parent_image_path = buffer.value
        finally:
            kernel32.CloseHandle(process_handle)
    except Exception:
        parent_image_path = ""
    parent_name = os.path.basename(parent_image_path).lower()
    if parent_name not in ("cmd.exe", "powershell.exe", "pwsh.exe"):
        return False

    import signal

    os.kill(parent_pid, signal.SIGTERM)
    return True


# =========================
# path related


def make_abs_path_relative_to_file(path: str, file: str) -> str:
    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)
    return path


# =========================
# file read/write


def write_file(path: str, lines: list[str], override=True, create_folder=True):

    if create_folder == True:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    with open(path, "w" if override else "a", encoding="utf-8") as f:
        f.writelines(lines)


def read_file(path: str):

    with open(path, encoding="utf-8") as f:
        return f.readlines()


# =========================
# helper functions


def _get_candidate_hwnds() -> list[int]:
    import ctypes

    kernel32_DLL = ctypes.WinDLL("kernel32", use_last_error=True)  # type:ignore
    user32_DLL = ctypes.WinDLL("user32", use_last_error=True)

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


def _helper_refresh_nonclient_area(hwnd: int) -> None:
    import ctypes

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


def _process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False

    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not process_handle:
            return ctypes.get_last_error() == 5  # ERROR_ACCESS_DENIED means the process still exists.
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(process_handle)
    except Exception:
        return False


def _wait_until_process_stops(pid: int, timeout_seconds: float) -> bool:
    import time

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _process_is_running(pid):
            return True
        time.sleep(0.1)
    return not _process_is_running(pid)


def _stop_process_tree(pid: int) -> str:
    if not _process_is_running(pid):
        return ""
    cmd = ["taskkill", "/PID", str(pid), "/T"]
    try:
        graceful_result = subprocess.run(  # noqa:S603
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    except FileNotFoundError:
        import signal

        os.kill(pid, signal.SIGTERM)
        return ""

    graceful_output = (graceful_result.stdout or "").strip()
    if graceful_result.returncode == 0 and _wait_until_process_stops(pid, 2.0):
        return graceful_output

    if not _process_is_running(pid):
        return graceful_output
    forced_result = subprocess.run(  # noqa:S603
        cmd + ["/F"],  # force
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    forced_output = (forced_result.stdout or "").strip()
    if forced_result.returncode == 0 or _wait_until_process_stops(pid, 2.0):
        return "\n".join(output for output in [graceful_output, forced_output] if output)

    detail = forced_output or graceful_output
    if detail:
        raise RuntimeError(detail)
    raise RuntimeError(f"taskkill failed with exit code {forced_result.returncode}")


def _read_process_id_entries(path: str) -> list[tuple[int, str]]:

    lines = read_file(path)

    out = []
    for line in lines:
        line = line.strip()
        if line != "":
            process_id_text = line.split(maxsplit=1)[0]
            try:
                out.append((int(process_id_text), line))
            except ValueError:
                pass
    return out


def _write_process_id_lines(path: str, lines: list[str]) -> None:
    non_empty_lines = [line if line.endswith("\n") else line + "\n" for line in lines if line.strip()]
    if non_empty_lines:
        write_file(path, non_empty_lines)
    elif os.path.exists(path):
        os.remove(path)


def _format_bytes(num_bytes) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            else:
                return f"{size:.2f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def _get_folder_size(folder: str | os.PathLike[str]) -> int:
    total = 0
    for root, _dirs, files in os.walk(folder):
        for filename in files:
            path = os.path.join(root, filename)
            try:
                if os.path.isfile(path):
                    total += os.path.getsize(path)
            except (OSError, PermissionError):
                pass
    return total


# =========================
# pid/process related


def get_running_processes_from_pid_file(pid_path: str) -> tuple[list[int], int]:
    """returns (running_process_ids, stale_count)"""

    if pid_path == "" or not os.path.exists(pid_path):
        return [], 0

    process_id_entries = _read_process_id_entries(pid_path)
    if not process_id_entries:
        os.remove(pid_path)
        return [], 0

    running_process_ids = []
    stale_count = 0
    seen_process_ids: set[int] = set()
    for process_id, _line in process_id_entries:
        if process_id in seen_process_ids:
            continue
        seen_process_ids.add(process_id)

        if _process_is_running(process_id):
            running_process_ids.append(process_id)
        else:
            stale_count += 1

    _write_process_id_lines(pid_path, [f"{process_id}\n" for process_id in running_process_ids])
    return running_process_ids, stale_count


def stop_processes_from_pid_file(pid_path: str) -> tuple[int, int, list[str]]:
    """returns (stopped_count, stale_count, failed_messages)"""
    if pid_path == "" or not os.path.exists(pid_path):
        return 0, 0, []

    process_id_entries = _read_process_id_entries(pid_path)
    if not process_id_entries:
        os.remove(pid_path)
        return 0, 0, []

    lines_by_process_id: dict[int, list[str]] = {}
    for process_id, line in process_id_entries:
        lines_by_process_id.setdefault(process_id, []).append(line)

    failed_lines = []
    failed_messages = []
    stopped_count = 0
    stale_count = 0
    for process_id, lines in lines_by_process_id.items():
        if not _process_is_running(process_id):
            stale_count += 1
            continue

        try:
            _stop_process_tree(process_id)
            stopped_count += 1
        except Exception as process_error:
            failed_lines.extend(lines)
            failed_messages.append(f"{process_id}: {process_error}")

    _write_process_id_lines(pid_path, failed_lines)
    return stopped_count, stale_count, failed_messages


# =========================
# python version related


def get_python_version():
    return subprocess.check_output(  # noqa:S603
        [
            python_exe_path,
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
        ],
        stderr=subprocess.STDOUT,
        text=True,
    ).strip()


def is_python_version_compatible(actual_version, required_version):

    actual_parts = actual_version.split(".")
    required_parts = required_version.strip().split(".")

    if (len(actual_parts) != 3) or (any(not part.isdigit() for part in actual_parts)):
        raise ValueError(
            f"Could not determine Python version from output: {actual_version}. Expected format like '3.13.2'."
        )

    if not required_parts or any(not part.isdigit() for part in required_parts):
        raise ValueError(
            f"Invalid target_version format: {required_version}. Must be a string like '3', '3.13', or '3.13.2'."
        )

    return actual_parts[: len(required_parts)] == required_parts


def read_python_version_from_file():

    if not os.path.exists(python_version_indicator_file_path):
        print_warn(f'[Error] missing file "{python_version_indicator_file_path}". Using Fallback determination.')
        return get_python_version()

    try:
        return read_file(python_version_indicator_file_path)[0].strip()
    except Exception:
        print_warn("[Error] Failed to determine python version from file. Using Fallback determination.")
        return get_python_version()


def save_python_version_to_file():
    current_version = get_python_version()
    write_file(python_version_indicator_file_path, [current_version])


def is_python_version_correct(target_version: str | float | int) -> tuple[bool, str | None]:
    """
    Returns whether the Python executable at ``exe_path`` matches ``target_version`` and the actual version:
        if target_version in [None, False, ""]:
            return [True,None]
        else:
            returns: [match,current_verison]

    Matching is prefix-based on proven version components:
    - If ``target_version`` is ``"3"``, any Python 3.x matches.
    - If ``target_version`` is ``"3.13"``, any Python 3.13.x matches.
    - If ``target_version`` is ``"3.13.2"``, only Python 3.13.2 matches.
    """
    if target_version in [None, False, ""]:
        return (True, None)

    if isinstance(target_version, (float, int)):
        target_version = str(target_version)

    found_version = read_python_version_from_file()

    return (is_python_version_compatible(found_version, target_version), found_version)


# =========================
# python/venv setup


def delete_venv() -> bool:
    return delete_folder_safe(
        venv_dir_path,
        prompt_for_confirmation=False,
        allowed_base=python_scripts_dir,
        expected_name=os.path.basename(venv_dir_path),
    )


def delete_python_distro() -> bool:
    return delete_folder_safe(
        python_dist_path,
        prompt_for_confirmation=False,
        allowed_base=python_scripts_dir,
        expected_name=os.path.basename(python_dist_path),
    )


def recreate_python_distro() -> None:

    delete_python_distro()

    subprocess.run(  # noqa
        [
            "cmd.exe",
            "/d",
            "/c",
            "call",
            portable_python_installer_path,
            python_version,
            py_env_dir,
            "1" if install_tkinter else "0",
            "1" if install_tests else "0",
            "1" if install_tools else "0",
            "0",  # dont install docs
        ],
        check=True,
    )

    if not os.path.exists(python_exe_path):
        raise RuntimeError(f'Portable Python installation did not produce expected file at "{python_exe_path}"')
    else:
        save_python_version_to_file()


def recreate_venv() -> None:

    delete_venv()

    subprocess.run(  # noqa
        ["cmd.exe", "/d", "/c", "call", portable_venv_creator_path, py_env_dir, rel_path_py_env_to_python_dist],
        check=True,
    )

    if not os.path.exists(venv_exe_path):
        raise RuntimeError(f'Portable virtual environment creator did not produce "{venv_exe_path}"')


def prompt_for_distro_reinstall(msg="Reinstall distro / recreate virtual environment?"):
    """
    Return int in prints below for cases in print:
        print("0. Leave current Python version and venv")
        print("1. Change Python version + Recreate venv with default packages")
        print("2. Change Python version + Recreate venv without packages")
        print("3. Change Python version + Recreate venv with current packages")
        print("4. Change Python version + Recreate venv with current packages + set them default")
        print("5. Change Python version + Recreate venv with auto-determined needed packages")
        print("6. Change Python version + Recreate venv with auto-determined needed packages + set them default")
    """
    print_warn(msg)
    print()
    print_warn("0. Leave current Python version and venv")
    print_warn("1. Change Python version + Recreate venv with default packages")
    print_warn("2. Change Python version + Recreate venv without packages")
    print_warn("3. Change Python version + Recreate venv with current packages")
    print_warn("4. Change Python version + Recreate venv with current packages + set them default")
    print_warn("5. Change Python version + Recreate venv with auto-determined needed packages")
    print_warn("6. Change Python version + Recreate venv with auto-determined needed packages + set them default")

    while True:
        choice = input_warn("Choose an option [1-6]: ").strip()

        if choice in {"0", "1", "2", "3", "4", "5", "6"}:
            return int(choice)

        print_warn("Invalid choice. Please enter 0, 1, 2, 3, 4, 5, or 6.")


def ensure_python_distro_and_venv(
    check_auto_determine_flag_for_default_package_install=True, set_icon_for_slow=False, app_id_for_slow=None
) -> None:

    if app_id_for_slow in [None, False]:
        app_id_for_slow = ""

    if not os.path.exists(python_exe_path):  # no python distro existing case:
        if set_icon_for_slow:
            set_terminal_icon_once()
        if app_id_for_slow != "":
            set_app_id_once(app_id_for_slow)
        print("\n" * 5)
        print("[Info] Python distribution not found. Installing portable Python:")
        recreate_python_distro()
        recreate_venv()
        install_default_packages(check_auto_determine_flag=check_auto_determine_flag_for_default_package_install)

    else:  # alread existing python distro case:
        if python_version not in ["", None]:
            matching, actual_version = is_python_version_correct(python_version)
        else:
            matching = True

        if matching == True:  # right python version case:
            if get_auto_search_phrase_state() == True:
                if set_icon_for_slow:
                    set_terminal_icon_once()
                if app_id_for_slow != "":
                    set_app_id_once(app_id_for_slow)
                print(
                    f'[Info] Found flag "{variable_in_default_packages_path_that_triggers_search_if_true} = True" in default packages file "{default_packages_file_path}"'
                )
                print(
                    "--> Auto determine needed packages and install them in recreated venv and set them as new defaults if success."
                )
                success, p = save_requirements_of_root_folder_noVersion()
                if success == True:
                    install_packages_from_file(p)
                    save_current_packages_as_default(auto_search_phrase_state=False)
                else:
                    print("[Warning] Failed to auto determine needed packages (see above).")

        else:  # wrong python version case:
            answer = prompt_for_distro_reinstall(
                f"[Warning] Python version in settings ({python_version}) is not matching the current one ({actual_version}). Please enter how to proceed:"  # type:ignore
            )

            if answer == 0:
                return
            elif answer in [1, 2, 3, 4, 5]:
                if set_icon_for_slow:
                    set_terminal_icon_once()
                if app_id_for_slow != "":
                    set_app_id_once(app_id_for_slow)
                recreate_python_distro()
                if answer == 1:
                    recreate_venv()
                    install_default_packages(
                        check_auto_determine_flag=check_auto_determine_flag_for_default_package_install
                    )
                elif answer == 2:
                    recreate_venv()
                elif answer in [3, 4]:
                    p = save_current_packages(with_version=False)
                    recreate_venv()
                    install_packages_from_file(p)
                    if answer == 4:
                        save_current_packages_as_default()
                elif answer in [5, 6]:
                    recreate_venv()
                    success, p = save_requirements_of_root_folder_noVersion()
                    if success == True:
                        install_packages_from_file(p)
                        if answer == 6:
                            save_current_packages_as_default()
                    else:
                        print(
                            "[Warning] Failed to auto determine needed packages (see above). Installing default packages instead:"
                        )
                        install_default_packages(check_auto_determine_flag=False)
            else:
                raise ValueError(f"Invalid answer: {answer}")


# ========================
# package related


def install_packages_from_file(path: str, *, upgrade: bool = True, no_cache: bool = True) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f'Package list not found: "{path}"')

    print()
    print(f'[Info] Package list: "{path}"')

    packages = read_file(path)
    for line in packages:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            break
    else:
        print("[Info] No packages to install.")
        return

    extra_commands: list[str] = []
    if upgrade:
        extra_commands.append("--upgrade")
    if no_cache:
        extra_commands.append("--no-cache-dir")

    subprocess.run(  # noqa
        [
            "cmd.exe",
            "/d",
            "/c",
            "call",
            venv_exe_path,
            "-m",
            "pip",
            "install",
            "-r",
            path,
            "--disable-pip-version-check",
            *extra_commands,
        ],
        check=True,
    )


def install_default_packages(check_auto_determine_flag=True):

    if check_auto_determine_flag == True:
        if get_auto_search_phrase_state() == True:
            print(
                f'[Info] Found flag "{variable_in_default_packages_path_that_triggers_search_if_true} = True" in default packages file "{default_packages_file_path}"'
            )
            print(
                "--> Auto determine needed packages and install them in recreated venv and set them as new defaults if success."
            )

            success, p = save_requirements_of_root_folder_noVersion()

            if success:
                install_packages_from_file(p)
                save_current_packages_as_default(auto_search_phrase_state=False)
            else:
                print_warn("[Error] Failed to auto determine required Python packages.")
                input_warn("Aborting. Press enter to exit")

    install_packages_from_file(default_packages_file_path)


def get_auto_search_phrase_state() -> bool | None:
    if not os.path.exists(default_packages_file_path):
        return None

    lines = read_file(default_packages_file_path)

    for line in lines:
        if variable_in_default_packages_path_that_triggers_search_if_true not in line:
            continue
        value = (
            line.replace(variable_in_default_packages_path_that_triggers_search_if_true, "")
            .replace("=", "")
            .replace("#", "")
            .strip()
            .lower()
        )
        if value == "true":
            return True
        if value == "false":
            return False
        return None
    return None


def save_current_packages_as_default(auto_search_phrase_state=None, with_version=True):
    if auto_search_phrase_state is None:
        auto_search_phrase_state = get_auto_search_phrase_state()

    packages = get_current_packages(with_version=with_version)

    write_file(
        default_packages_file_path,
        [
            f"{variable_in_default_packages_path_that_triggers_search_if_true} = {auto_search_phrase_state}",
            "",
            *packages,
        ],
    )


def get_installed_packages(exe_path, with_version=True):
    result = subprocess.run(  # noqa
        [exe_path, "-m", "pip", "--disable-pip-version-check", "freeze"],
        capture_output=True,
        text=True,
        check=True,
    )
    packages_with_version = result.stdout.strip().splitlines()

    if with_version == True:
        return packages_with_version
    else:
        packages_without_version = []

        for line in packages_with_version:
            line = line.strip()

            if line == "" or line.startswith("#"):
                continue

            for operator in ("===", "==", "~=", ">=", "<=", "!=", ">", "<"):
                if operator in line:
                    packages_without_version.append(line.split(operator, 1)[0].strip())
                    break
            else:
                packages_without_version.append(line)

        return packages_without_version


def get_current_packages(with_version=True):
    return get_installed_packages(exe_path=venv_exe_path, with_version=with_version)


def save_installed_packages(exe_path, output_path=None, with_version=True):

    if output_path is None:
        if with_version == True:
            output_path = determined_current_packages_file_path_withVersion
        else:
            output_path = determined_current_packages_file_path_noVersion
    else:
        output_path = os.path.abspath(output_path)

    packages = get_installed_packages(with_version=with_version, exe_path=exe_path)

    write_file(output_path, packages)

    return output_path


def save_current_packages(output_path=None, with_version=True):
    return save_installed_packages(output_path=output_path, with_version=with_version, exe_path=venv_exe_path)


def save_requirements_of_root_folder_noVersion(
    output_path=determined_needed_packages_output_file_path_noVersion,
) -> tuple[bool, str]:
    """reuturns success,output_path"""

    output_path = os.path.abspath(output_path)

    if os.path.exists(output_path):
        os.remove(output_path)

    try:
        cmd = [
            sys.executable,
            "-m",
            "pipreqs.pipreqs",
            python_scripts_dir,  # searched_folder,
            "--force",
            "--savepath",
            output_path,
            "--ignore",
            ",".join(excluded_folders_for_package_search),  # excluded_folders
            "--encoding",
            "utf-8",
            "--mode",
            "no-pin",
            "--no-follow-links",
        ]

        if os.path.exists(output_path):
            print()
            print("=" * 20)
            print("Start of finding required python packages")
            print("-" * 20)
            subprocess.run(cmd, check=True)  # noqa
            print("-" * 20)
            print(f'End of finding required python packages. Result: "{output_path}":\n')
            packages = read_file(output_path)
            print(*packages)
            print("=" * 20)
            print()

            success = True

        else:
            success = False
            print()
            print_warn("[Error] Failed to auto determine needed packages (see above)")
    except Exception as e:
        print()
        print_warn(f"[Error] Failed to auto determine packages (do you have internet?): {e}")
        success = False

    return success, output_path


def save_requirements_of_root_folder_withVersion(
    output_path: str = determined_needed_packages_output_file_path_withVersion,
):
    """returns success bool"""

    import shutil  # lazy import because slow
    import tempfile  # lazy import because only here

    temp_venv = tempfile.mkdtemp(prefix="pyapp_template_package_pin_")
    temp_python = temp_venv + "\\Scripts\\python.exe"

    try:
        output_path = os.path.normpath(os.path.abspath(output_path))

        success, output_path_noVersion = save_requirements_of_root_folder_noVersion()

        if success == False:
            return False

        ensure_python_distro_and_venv()

        subprocess.run([python_exe_path, "-m", "venv", temp_venv], check=True)  # noqa
        if not os.path.exists(temp_python):
            raise RuntimeError(f'Temporary environment did not create "{temp_python}"')

        subprocess.run(  # noqa
            [temp_python, "-m", "pip", "install", "-r", output_path_noVersion, "--disable-pip-version-check"],
            check=True,
        )

        save_installed_packages(exe_path=temp_python, output_path=output_path, with_version=True)

        return True

    except Exception as e:
        print()
        print_warn(f"[Error] Failed to auto determine packages: {e}")
        return False

    finally:
        shutil.rmtree(temp_venv, ignore_errors=True)


# ========================
