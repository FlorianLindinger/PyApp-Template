# launch script in wrapper that handles:
#   errors
#   return
#   icon setting
#   terminal-renaming
#   working dir setting
#   app-id setting
#   closer or keep open logic on finish/error/fail
#   print in additional terminal for final print info if in no-terminal mode
#   ...

try:
    # ==================
    # import

    import atexit
    import builtins
    import faulthandler
    import os
    import runpy
    import sys

    # ==================
    # handle args

    def arg_to_bool(index: int, default: bool = False) -> bool:
        if len(sys.argv) <= index:
            return default
        return sys.argv[index].strip().lower() in {"1", "true", "yes", "on"}

    def arg_to_wav_path(index: int) -> str:
        if len(sys.argv) <= index:
            return ""
        wav_path = sys.argv[index].strip()
        if wav_path != "" and os.path.splitext(wav_path)[1].lower() != ".wav":
            raise ValueError(f'[Error] Sound argument must be empty or a .wav file: "{wav_path}"')
        return wav_path

    script_path = sys.argv[1]

    title = sys.argv[2]
    icon_path = sys.argv[3]
    app_id = sys.argv[4]
    wdir_is_script_dir = arg_to_bool(5)
    close_on_python_interpreter_crash = arg_to_bool(6)
    close_on_failure = arg_to_bool(7)
    close_on_success = arg_to_bool(8)
    print_timestamp_format = sys.argv[9]
    log_path = sys.argv[10]
    log_timestamp_format = sys.argv[11]
    overwrite_log = arg_to_bool(12)
    script_after_interpreter_crash_path = sys.argv[13]
    input_prepend = sys.argv[14]
    process_id_file_path = sys.argv[15]
    play_sound_on_success = arg_to_wav_path(16)
    send_Windows_notification_on_success = arg_to_bool(17)
    play_sound_on_failure = arg_to_wav_path(18)
    send_Windows_notification_on_failure = arg_to_bool(19)
    play_sound_on_python_interpreter_crash = arg_to_wav_path(20)
    send_Windows_notification_on_python_interpreter_crash = arg_to_bool(21)

    terminal_colors = sys.argv[22]
    script_has_terminal = arg_to_bool(23)
    # script_has_terminal = true means that this window is run in a terminal and False that it is invisible and one needs to create a new terminal to print

    # ==================

    if app_id != "" or script_has_terminal:
        import ctypes

    if process_id_file_path != "":

        def remove_own_process_id_file_entries(path: str, process_id: int) -> None:
            try:
                with open(path, encoding="utf-8") as pid_file:
                    lines = pid_file.readlines()

                own_process_id = str(process_id)
                remaining_lines = []
                for line in lines:
                    parts = line.strip().split(maxsplit=1)
                    if parts and parts[0] == own_process_id:
                        continue
                    remaining_lines.append(line)

                if any(line.strip() for line in remaining_lines):
                    with open(path, "w", encoding="utf-8") as pid_file:
                        pid_file.writelines(remaining_lines)
                else:
                    os.remove(path)
            except FileNotFoundError:
                pass
            except Exception:
                pass

        try:
            own_process_id = os.getpid()
            with open(process_id_file_path, "a", encoding="utf-8") as pid_file:
                pid_file.write(f"{own_process_id}\n")
            atexit.register(
                remove_own_process_id_file_entries,
                process_id_file_path,
                own_process_id,
            )
        except Exception as e:
            print(f"[Warning] Failed to write script-wrapper PID file: {e}")

    # ==================
    # define functons and variables

    ANSI_WARN = "\x1b[1;37;41m"  # white text, red bg, bold
    ANSI_SUCCESS = "\x1b[1;37;42m"  # white text, green bg, bold
    ANSI_RESET = "\033[0m"

    WINDOWS_CRASH_CODES = {
        0xC0000005,  # access violation
        0xC00000FD,  # stack overflow
        0xC000001D,  # illegal instruction
        0xC0000096,  # privileged instruction
        0xC0000409,  # stack buffer overrun
    }

    def unsigned32(n: int) -> int:
        return n & 0xFFFFFFFF

    def looks_like_interpreter_crash(returncode) -> bool:
        return isinstance(returncode, int) and (unsigned32(returncode) in WINDOWS_CRASH_CODES)

    def print_warn(msg, sep: str | None = " ", end: str | None = "\n"):
        print(f"{ANSI_WARN}{msg}{ANSI_RESET}", sep=sep, end=end)

    def input_warn(msg):
        input(f"{ANSI_WARN}{msg}{ANSI_RESET}")

    def input_success(msg):
        input(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}")

    def set_terminal_name(name: str) -> None:
        try:
            clean_name = name.replace("\r\n", "").replace("\r", "")
            os.system(f"title {clean_name}")  # noqa:S605
        except Exception:
            pass

    def run_text_in_new_terminal_and_wait(text):
        import subprocess  # noqa:PLC0415
        import sys  # noqa

        subprocess.run(  # noqa:S603
            [sys.executable, "-X", "faulthandler", "-c", text], creationflags=subprocess.CREATE_NEW_CONSOLE
        )

    def play_windows_sound(wav_path: str) -> None:
        try:
            import winsound

            sound = wav_path
            if not os.path.isabs(sound):
                sound = os.path.join(r"C:\Windows\Media", sound)
            winsound.PlaySound(
                sound,
                winsound.SND_FILENAME | winsound.SND_NODEFAULT,
            )
        except Exception:
            pass

    def send_windows_notification(notification_title: str, message: str) -> None:
        import subprocess  # noqa:PLC0415
        powershell_script = r"""
$titleText = if ($args.Count -gt 0) { $args[0] } else { "Python script" }
$messageText = if ($args.Count -gt 1) { $args[1] } else { "" }
$appId = if ($args.Count -gt 2 -and $args[2]) { $args[2] } else { "PyAppTemplate" }
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] | Out-Null
$titleXml = [System.Security.SecurityElement]::Escape($titleText)
$messageXml = [System.Security.SecurityElement]::Escape($messageText)
$xml = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>$titleXml</text>
      <text>$messageXml</text>
    </binding>
  </visual>
  <audio silent="true"/>
</toast>
"@
$doc = [Windows.Data.Xml.Dom.XmlDocument]::new()
$doc.LoadXml($xml)
$toast = [Windows.UI.Notifications.ToastNotification]::new($doc)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
"""
        try:
            subprocess.Popen(  # noqa:S603
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    powershell_script,
                    notification_title,
                    message,
                    app_id,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            pass

    def run_completion_alerts(kind: str, exit_code) -> None:
        play_sound_by_kind = {
            "success": play_sound_on_success,
            "failure": play_sound_on_failure,
            "crash": play_sound_on_python_interpreter_crash,
        }
        notification_by_kind = {
            "success": send_Windows_notification_on_success,
            "failure": send_Windows_notification_on_failure,
            "crash": send_Windows_notification_on_python_interpreter_crash,
        }
        messages = {
            "success": "Script finished successfully.",
            "failure": f"Script exited with code {exit_code}.",
            "crash": f"Python process crashed with code {exit_code}.",
        }

        if notification_by_kind.get(kind, False):
            send_windows_notification(f"{title}: {kind.title()}", messages.get(kind, f"Script ended with {exit_code}."))
        sound_setting = play_sound_by_kind.get(kind)
        if sound_setting:
            play_windows_sound(sound_setting)

    if script_has_terminal:
        from ctypes import wintypes

        def get_terminal_name():
            try:
                buffer = ctypes.create_unicode_buffer(1024)
                ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))
                return str(buffer.value)
            except Exception:
                return "Terminal"

        def set_terminal_icon(icon_path: str, print_errors: bool = False, app_id: str = "") -> int:
            """Change the icon of the current terminal window and return the first touched hwnd."""

            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1
            IMAGE_ICON = 1
            GA_ROOTOWNER = 3

            LR_LOADFROMFILE = 0x0010
            LR_DEFAULTSIZE = 0x0040

            SM_CXICON = 11
            SM_CYICON = 12
            SM_CXSMICON = 49
            SM_CYSMICON = 50
            GCLP_HICON = -14
            GCLP_HICONSM = -34
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            SWP_FRAMECHANGED = 0x0020

            if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_longlong):
                signed_ptr = ctypes.c_longlong
            else:
                signed_ptr = ctypes.c_long

            hinstance_type = getattr(wintypes, "HINSTANCE", wintypes.HANDLE)
            wparam_type = getattr(wintypes, "WPARAM", ctypes.c_size_t)
            lparam_type = getattr(wintypes, "LPARAM", signed_ptr)
            lresult_type = getattr(wintypes, "LRESULT", signed_ptr)

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            user32 = ctypes.WinDLL("user32", use_last_error=True)

            kernel32.GetConsoleWindow.argtypes = []
            kernel32.GetConsoleWindow.restype = wintypes.HWND

            kernel32.GetConsoleTitleW.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
            kernel32.GetConsoleTitleW.restype = wintypes.DWORD

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

            user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
            user32.FindWindowW.restype = wintypes.HWND

            user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
            user32.GetAncestor.restype = wintypes.HWND

            user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
            user32.GetClassNameW.restype = ctypes.c_int

            user32.GetSystemMetrics.argtypes = [ctypes.c_int]
            user32.GetSystemMetrics.restype = ctypes.c_int

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

            user32.LoadImageW.argtypes = [
                hinstance_type,
                wintypes.LPCWSTR,
                wintypes.UINT,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.UINT,
            ]
            user32.LoadImageW.restype = wintypes.HANDLE

            user32.SendMessageW.argtypes = [
                wintypes.HWND,
                wintypes.UINT,
                wparam_type,
                lparam_type,
            ]
            user32.SendMessageW.restype = lresult_type

            if hasattr(user32, "SetClassLongPtrW"):
                set_class_long = user32.SetClassLongPtrW
                set_class_long.argtypes = [wintypes.HWND, ctypes.c_int, signed_ptr]
                set_class_long.restype = ctypes.c_size_t
            else:
                set_class_long = user32.SetClassLongW
                set_class_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
                set_class_long.restype = wintypes.DWORD

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

            def format_last_error(prefix: str) -> str:
                error_code = ctypes.get_last_error()
                if error_code == 0:
                    return prefix
                return f"{prefix} ({error_code}: {ctypes.FormatError(error_code).strip()})"

            def get_console_title() -> str:
                buffer = ctypes.create_unicode_buffer(1024)
                title_length = kernel32.GetConsoleTitleW(buffer, len(buffer))
                if title_length == 0:
                    return ""
                return buffer.value

            def get_window_text(hwnd: int) -> str:
                if hwnd == 0:
                    return ""
                text_length = user32.GetWindowTextLengthW(hwnd)
                buffer = ctypes.create_unicode_buffer(text_length + 1)
                user32.GetWindowTextW(hwnd, buffer, len(buffer))
                return buffer.value

            def get_window_class_name(hwnd: int) -> str:
                if hwnd == 0:
                    return ""
                buffer = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, buffer, len(buffer))
                return buffer.value

            def get_root_owner(hwnd: int) -> int:
                if hwnd == 0:
                    return 0
                return int(user32.GetAncestor(hwnd, GA_ROOTOWNER) or 0)

            def get_window_process_id(hwnd: int) -> int:
                if hwnd == 0:
                    return 0
                process_id = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
                return int(process_id.value)  # type:ignore

            def get_process_image_path(process_id: int) -> str:
                if process_id == 0:
                    return ""

                process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
                if not process_handle:
                    return ""

                try:
                    buffer_length = wintypes.DWORD(32768)
                    buffer = ctypes.create_unicode_buffer(buffer_length.value)
                    if kernel32.QueryFullProcessImageNameW(process_handle, 0, buffer, ctypes.byref(buffer_length)):
                        return buffer.value
                    return ""
                finally:
                    kernel32.CloseHandle(process_handle)

            def describe_window(hwnd: int) -> str:
                if hwnd == 0:
                    return "hwnd=0x0"

                process_id = get_window_process_id(hwnd)
                return (
                    f"hwnd=0x{hwnd:016X}, "
                    f"class={get_window_class_name(hwnd)!r}, "
                    f"title={get_window_text(hwnd)!r}, "
                    f"visible={bool(user32.IsWindowVisible(hwnd))}, "
                    f"pid={process_id}, "
                    f"process={get_process_image_path(process_id)!r}"
                )

            def iter_candidate_windows() -> list[int]:
                candidate_hwnds: list[int] = []

                def add(hwnd: int) -> None:
                    if hwnd == 0 or not user32.IsWindow(hwnd) or hwnd in candidate_hwnds:
                        return
                    candidate_hwnds.append(hwnd)

                console_hwnd = int(kernel32.GetConsoleWindow() or 0)
                console_title = get_console_title()

                add(console_hwnd)
                add(get_root_owner(console_hwnd))

                if console_title:
                    hwnd_by_console_class = int(user32.FindWindowW("ConsoleWindowClass", console_title) or 0)
                    add(hwnd_by_console_class)
                    add(get_root_owner(hwnd_by_console_class))

                    hwnd_by_title = int(user32.FindWindowW(None, console_title) or 0)
                    add(hwnd_by_title)
                    add(get_root_owner(hwnd_by_title))

                return candidate_hwnds

            def load_icon(path: str, width: int, height: int) -> int:
                icon_handle = user32.LoadImageW(None, path, IMAGE_ICON, width, height, LR_LOADFROMFILE)
                if not icon_handle:
                    icon_handle = user32.LoadImageW(None, path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
                if not icon_handle:
                    raise OSError(format_last_error(f'Failed to load icon from "{path}"'))
                return int(icon_handle)

            def set_class_icon(hwnd: int, index: int, icon_handle: int) -> None:
                ctypes.set_last_error(0)
                set_class_long(hwnd, index, icon_handle)
                if ctypes.get_last_error() != 0:
                    raise OSError(format_last_error(f"Failed to update window class icon for hwnd 0x{hwnd:016X}"))

            def refresh_nonclient_area(hwnd: int) -> None:
                user32.SetWindowPos(
                    hwnd,
                    None,
                    0,
                    0,
                    0,
                    0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
                )

            def set_terminal_window_app_id(candidate_hwnds: list[int], app_id: str, print_errors: bool = False) -> int:
                """Try to set System.AppUserModel.ID on the terminal window itself."""
                import uuid  # noqa:PLC0415

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

                                refresh_nonclient_area(hwnd)
                                changed_count += 1
                            finally:
                                if property_store:
                                    property_store.contents.lpVtbl.contents.Release(property_store)
                        except Exception as error:
                            if print_errors:
                                print(f"[Info] AppID update skipped for hwnd 0x{hwnd:016X}: {error}")
                finally:
                    if should_uninitialize:
                        ole32.CoUninitialize()

                return changed_count

            normalized_icon_path = os.path.abspath(os.path.expanduser(icon_path))
            if not os.path.isfile(normalized_icon_path):
                raise FileNotFoundError(f'Icon file not found: "{normalized_icon_path}"')

            candidate_hwnds = iter_candidate_windows()
            if print_errors:
                print(f'[Info] Icon path: "{normalized_icon_path}"')
                print(f"[Info] WT_SESSION set: {bool(os.environ.get('WT_SESSION'))}")
                print(f"[Info] Console title: {get_console_title()!r}")
                print("[Info] Candidate windows:")
                if candidate_hwnds:
                    for hwnd in candidate_hwnds:
                        print(f"  - {describe_window(hwnd)}")
                else:
                    print("  - none")

            if not candidate_hwnds:
                raise RuntimeError("Could not find the current terminal window.")

            small_icon = load_icon(
                normalized_icon_path,
                user32.GetSystemMetrics(SM_CXSMICON),
                user32.GetSystemMetrics(SM_CYSMICON),
            )
            large_icon = load_icon(
                normalized_icon_path,
                user32.GetSystemMetrics(SM_CXICON),
                user32.GetSystemMetrics(SM_CYICON),
            )

            for hwnd in candidate_hwnds:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small_icon)
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, large_icon)
                try:
                    set_class_icon(hwnd, GCLP_HICONSM, small_icon)
                    set_class_icon(hwnd, GCLP_HICON, large_icon)
                except OSError as error:
                    if print_errors:
                        print(f"[Info] Class icon update skipped for hwnd 0x{hwnd:016X}: {error}")
                refresh_nonclient_area(hwnd)

            if print_errors:
                print(f"[Info] Attempted icon update on {len(candidate_hwnds)} window(s).")

            if app_id != "":
                try:
                    changed_count = set_terminal_window_app_id(candidate_hwnds, app_id, print_errors=print_errors)
                    if print_errors:
                        print(f"[Info] Attempted AppID update on {changed_count} terminal window(s).")
                except Exception as error:
                    if print_errors:
                        print(f"[Info] Terminal AppID update skipped: {error}")

            return candidate_hwnds[0]

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
                print_red: bool = False,
                auto_flush: bool = True,
            ) -> None:
                if print_stream is None:
                    raise ValueError("print_stream is required")

                self.print_stream = print_stream
                self.log_stream = log_stream
                self.print_timestamp_format = print_timestamp_format
                self.log_timestamp_format = log_timestamp_format
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
                            self.log_stream.write(part)

                        if part.endswith("\n"):
                            if self.print_red and self._print_supports_color():
                                self.print_stream.write(self.ANSI_RESET)
                            self._at_line_start = True
                        else:
                            self._at_line_start = False

                    if self.auto_flush:
                        self.flush()

                return len(data)

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
                print_timestamp_format=print_timestamp_format,
                log_timestamp_format=log_timestamp_format,
            )
            sys.stderr = pipe_splitter(
                sys.__stderr__,
                log_file,
                print_timestamp_format=print_timestamp_format,
                log_timestamp_format=log_timestamp_format,
                print_red=True,
            )
            if faulthandler.is_enabled():
                faulthandler.enable(file=log_file, all_threads=True)

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
        # set working directory
        if wdir_is_script_dir:
            os.chdir(os.path.dirname(script_path))

        # setup logging
        if log_path != "":
            setup_log_prints(log_path, overwrite_log)  # type:ignore

        # set app id for taskbar grouping (combining) of (Qt) GUI icon with launcher shortcut icon
        if app_id != "":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)  # type:ignore
            except Exception as e:
                print(e)

        # set terminal name
        if script_has_terminal:
            set_terminal_name(title)  # type:ignore
            set_terminal_icon(icon_path, app_id=app_id)  # type:ignore

            if terminal_colors != "":
                os.system(f"color {terminal_colors}")  # noqa:S605

        sys.argv = [
            script_path,
            icon_path,
            title,
            app_id,
            log_path,
            "1" if script_has_terminal else "01" if wdir_is_script_dir else "01" if close_on_failure else "0",
            "1" if close_on_success else "0",
        ]

        # change sys.path[0] to be dir of target script and not this script
        sys.path[0] = os.path.dirname(script_path)

        # run in the current python process and wait for finish
        original_input = builtins.input
        if input_prepend != "":

            def input_with_prepend(prompt=""):
                return original_input(f"{prompt}{input_prepend}")

            builtins.input = input_with_prepend
        try:
            runpy.run_path(script_path, run_name="__main__")
            # no crash:
            exit_code = 0
        except SystemExit as e:  # catch sys.exit
            exit_code = e.code
            if exit_code is None:
                exit_code = 0
        finally:
            builtins.input = original_input

        # change terminal and print depending on exit_code
        if exit_code == 0:
            if close_on_success:
                sys.exit(0)
            else:
                script = """
set_terminal_name(rf"[Success] {{get_terminal_name()}}")
print()
input_success("[Program finished successfully] Press Enter to exit.")
"""
                if script_has_terminal:
                    exec(script)  # noqa
                else:
                    if log_path != "":
                        print("[Program finished successfully]")
                    run_text_in_new_terminal_and_wait(script_base + script)
                sys.exit(0)
        elif looks_like_interpreter_crash(exit_code):
            if close_on_python_interpreter_crash:
                sys.exit(exit_code)
            else:
                ...  ################### WIP

        else:  # regular failure case (includes any string exit_code)
            if close_on_failure:
                sys.exit(exit_code)
            else:
                script = f"""
set_terminal_name(rf"[Failure] {{get_terminal_name()}}")
print()
print_warn(rf"[Python Failure Return] Script exited with code: {exit_code}")
input_warn("[Python Failure Return] Press Enter to exit.")
"""
                if script_has_terminal:
                    exec(script)  # noqa
                else:
                    run_text_in_new_terminal_and_wait(script_base + script)
                sys.exit(exit_code)

    except Exception as e:  # backend crash
        import sys
        import traceback

        try:  # attempt detailed error report
            script = f"""
set_terminal_name(rf"[Crash] {{get_terminal_name()}}")
print()
print_warn("="*40)
print_warn(r"CRITICAL LAUNCH ERROR: {e}")
print_warn("-"*40)
print_warn(r\"""{traceback.format_exc()}\""",end="")
print_warn("-"*40)
print_warn(r"[Info] Python Exe: {sys.executable}")
print_warn(r"[Info] Script: {script_path}")
print_warn("-"*40)
input_warn("[Python Crash] See above. Press Enter to exit.")
"""
            if script_has_terminal:
                exec(script)  # noqa
            else:
                run_text_in_new_terminal_and_wait(script_base + script)
            sys.exit(1)

        except Exception as inner_e:  # fallback to minimal error report. Always in new terminal for extra safety
            script = f"""
                print(f"[Error] Failed to handle crash: {inner_e}")
                print({traceback.format_exc()})
                input("Press Enter to exit.")
            """
            run_text_in_new_terminal_and_wait(script_base + script)
            sys.exit(1)


except Exception as e:
    import sys
    import traceback

    print("=" * 20)
    print(f"[Error] Failed in wrapper script with error: {e}:")
    print("-" * 20)
    print(traceback.format_exc())
    print("-" * 20)
    input("Press enter to exit")
    sys.exit(1)

finally:
    try:
        log_file.close()  # type:ignore
    except Exception:
        pass
    # sys.exit(number) is not altered by this "finally" block
