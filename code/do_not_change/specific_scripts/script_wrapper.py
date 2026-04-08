try:
    # add change icon

    # launch script in wrapper that handles:
    #   errors
    #   return
    #   icon setting
    #   terminal-renaming
    #   working dir setting
    #   app-id setting
    #   closer or keep open logic on finish/error/fail
    #   print in additional terminal for final print info if in no-terminal mode

    # ==================
    # import

    import atexit
    import ctypes
    import os
    import runpy
    import sys

    # ==================
    # handle args

    script_path = sys.argv[1]

    title = sys.argv[2]
    icon_path = sys.argv[3]
    app_id = sys.argv[4]
    wdir_is_script_dir = sys.argv[5] == "1"
    close_on_crash = sys.argv[6] == "1"
    close_on_failure = sys.argv[7] == "1"
    close_on_success = sys.argv[8] == "1"
    log_path_rel_to_wdir = sys.argv[9]

    terminal_colors = sys.argv[10]
    script_has_terminal = sys.argv[11] == "1"
    # script_has_terminal = "1" means that this window is run in a terminal and False that it is invisible and one needs to create a new terminal to print
    backend_python_exe_path = sys.argv[12]  # i guess safer for extra terminal print if the user python is broken

    # ==================
    # define functons and variables

    ASCI_RED = "\033[91m"
    ASCI_GREEN = "\033[92m"
    ASCI_RESET = "\033[0m"

    def print_red(msg, sep=" ", end="\n"):
        print(f"{ASCI_RED}{msg}{ASCI_RESET}", sep=sep, end=end)

    def print_green(msg, sep=" ", end="\n"):
        print(f"{ASCI_GREEN}{msg}{ASCI_RESET}", sep=sep, end=end)

    def input_red(msg):
        input(f"{ASCI_RED}{msg}{ASCI_RESET}")

    def input_green(msg):
        input(f"{ASCI_GREEN}{msg}{ASCI_RESET}")

    def set_terminal_name(name: str) -> None:
        try:
            os.system(f"title {name.replace('r\n', '').replace(r'\r', '')}")  # noqa:S605
        except Exception:
            pass

    def get_terminal_name():
        try:
            buffer = ctypes.create_unicode_buffer(1024)
            ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))
            return str(buffer.value)
        except Exception:
            return "Terminal"

    if script_has_terminal:
        from ctypes import wintypes

        def set_terminal_icon(icon_path: str, print_errors: bool = False) -> int:
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
                return int(process_id.value)

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

            return candidate_hwnds[0]

    def run_text_in_new_terminal_and_wait(text):
        import subprocess  # noqa:PLC0415

        subprocess.run([backend_python_exe_path, "-c", text], creationflags=subprocess.CREATE_NEW_CONSOLE)  # noqa:S603

    class pipe_splitter:
        """use like the following example to save prints and errors to log file and print to console at same time:
        log_file = open(Path("app.log"), "a", encoding="utf-8",buffering=1)
        sys.stdout = pipe_splitter(sys.__stdout__, log_file)
        """

        def __init__(self, *streams):
            self.streams = streams

        def write(self, data):
            for stream in self.streams:
                stream.write(data)
                stream.flush()

        def flush(self):
            for stream in self.streams:
                stream.flush()

    # used to print in new terminal window:
    script_base = r"""
    imoprt os,mctypes

    ASCI_RED = "\033[91m"
    ASCI_GREEN = "\033[92m"
    ASCI_RESET = "\033[0m"

    def print_red(msg, sep=" ", end="\n"):
        print(f"{ASCI_RED}{msg}{ASCI_RESET}", sep=sep, end=end)

    def print_green(msg, sep=" ", end="\n"):
        print(f"{ASCI_GREEN}{msg}{ASCI_RESET}", sep=sep, end=end)

    def input_red(msg):
        input(f"{ASCI_RED}{msg}{ASCI_RESET}")

    def input_green(msg):
        input(f"{ASCI_GREEN}{msg}{ASCI_RESET}")

    def set_terminal_name(name: str) -> None:
        try:
            os.system(f"title {name.replace('r\n', '').replace(r'\r', '')}")  # noqa:S605
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

    try:
        # set working directory
        if wdir_is_script_dir:
            os.chdir(os.path.dirname(script_path))

        if log_path_rel_to_wdir != "":
            log_file = open(log_path_rel_to_wdir, "w", encoding="utf-8", buffering=1)  # noqa:SIM115
            atexit.register(log_file.close)
            sys.stdout = pipe_splitter(sys.__stdout__, log_file)
            sys.stderr = pipe_splitter(sys.__stderr__, log_file)

        # set app id for taskbar grouping (combining) of (Qt) GUI icon with launcher shortcut icon
        if app_id != "":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            except Exception as e:
                print(e)

        # set terminal name
        if script_has_terminal:
            set_terminal_name(title)  # type:ignore
            set_terminal_icon(icon_path)  # type:ignore

            if terminal_colors != "":
                os.system(f"color {terminal_colors}")  # noqa:S605

        # run and wait for finish
        try:
            sys.argv = [
                script_path,
                icon_path,
                title,
                "1" if close_on_crash else "0",
                "1" if close_on_failure else "0",
                "1" if close_on_success else "0",
            ]
            runpy.run_path(script_path, run_name="__main__")
            exit_code = 0
        except SystemExit as e:
            if isinstance(e.code, int):
                exit_code = e.code
            elif e.code is None:
                exit_code = 0
            else:
                # e.code can be something else which is treated as error
                exit_code = 1

        # change terminal and print depending on exit_code
        if exit_code == 0:
            if close_on_success:
                sys.exit(0)
            else:
                if script_has_terminal:
                    set_terminal_name(f"[Success] {get_terminal_name()}")
                    print()
                    print_green("[Program finished successfully] ", end="")
                    input("Press Enter to exit.")
                else:
                    script = (
                        script_base
                        + """
    set_terminal_name(f"[Success] {get_terminal_name()}")
    print()
    print_green("[Program finished successfully] ",end="")
    input("Press Enter to exit.")
    """
                    )
                    run_text_in_new_terminal_and_wait(script)
        else:
            if close_on_failure:
                sys.exit(exit_code)
            else:
                if script_has_terminal:
                    set_terminal_name(f"[Failure] {get_terminal_name()}")
                    print()
                    print_red(f"[Python Failure Return] Script exited with code: {exit_code}")
                    input_red("[Python Failure Return] Press Enter to exit.")
                else:
                    script = (
                        script_base
                        + """
    set_terminal_name(f"[Failure] {get_terminal_name()}")
    print()
    print_red(f"[Python Failure Return] Script exited with code: {result.returncode}")
    input_red("[Python Failure Return] Press Enter to exit.")
    """
                    )
                    run_text_in_new_terminal_and_wait(script)

    except Exception as e:
        import traceback

        try:
            if close_on_crash:
                sys.exit(1)
            else:
                if script_has_terminal:
                    try:
                        set_terminal_name(f"[Crash] {get_terminal_name()}")
                    except Exception:
                        pass
                    print()
                    print_red("=" * 40)
                    print_red(f"CRITICAL LAUNCH ERROR: {e}")
                    print_red("=" * 40)
                    traceback.print_exc()
                    print_red("=" * 40)
                    print(f"[Info] Python Exe: {sys.executable}")
                    print(f"[Info] Script: {script_path}")
                    print()

                    input_red("[Python Crash] See above. Press Enter to exit.")
                else:
                    tb = traceback.print_exc()
                    script = (
                        script_base
                        + f"""
    set_terminal_name(f"[Crash] {{get_terminal_name()}}")
    print()
    print_red("="*40)
    print_red(f"CRITICAL LAUNCH ERROR: {e}")
    print_red("="*40)
    print({tb})
    print_red("="*40)
    print(f"[Info] Python Exe: {sys.executable}")
    print(f"[Info] Script: {script_path}")
    print()
    input_red("[Python Crash] See above. Press Enter to exit.")
    """
                    )
                    run_text_in_new_terminal_and_wait(script)

        except Exception as inner_e:
            tb = traceback.format_exc()

            script = (
                script_base
                + f"""
    print(f"[Error] Failed to handle crash: {{{inner_e}}}")
    print({tb})
    input("Press Enter to exit.")
    """
            )
            run_text_in_new_terminal_and_wait(script)


except Exception as e:
    import sys
    import traceback

    print(f"[Error] Failed in wrapper script with error: {e}:")
    print("=" * 20)
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
