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
    wdir_is_script_dir = sys.argv[5]
    close_on_crash = sys.argv[6]
    close_on_failure = sys.argv[7]
    close_on_success = sys.argv[8]
    log_path_rel_to_wdir = sys.argv[9]
    
    terminal_colors = sys.argv[10]
    script_has_terminal = sys.argv[11]
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
        if wdir_is_script_dir == "1":
            os.chdir(os.path.dirname(script_path))

        if log_path_rel_to_wdir != "":
            log_file = open(log_path_rel_to_wdir, "w", encoding="utf-8", buffering=1) #noqa:SIM115
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
        if script_has_terminal == "1":
            set_terminal_name(title)

            if terminal_colors != "":
                os.system(f"color {terminal_colors}")  # noqa:S605

        # run and wait for finish
        try:
            sys.argv = [script_path, icon_path, title, close_on_crash, close_on_failure, close_on_success]
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
                if script_has_terminal == "1":
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
                if script_has_terminal == "1":
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
                if script_has_terminal == "1":
                    set_terminal_name(f"[Crash] {get_terminal_name()}")
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
