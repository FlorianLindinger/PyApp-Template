"""WIP

This script is inteded to be launched in a visible terminal that is minimized on start. It will go to foreground on first print.
"""

# {e} will be formatted to exception:
fail_message = "[Error] Failed during program start: {e}"

try:
    # ==============================
    # import Python packages
    # ==============================

    import os
    import subprocess
    import sys
    import time

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
        program_name,
        start_minimized,
        tab_bar_color,
        use_classic_terminal,
        use_global_python,
    )
    from backend.DONT_CHANGE.scripts._common_code import (
        close_terminal,
        ensure_frontend_packages,
        input_warn,
        make_empty_args_safe,
        print_traceback,
        print_warn,
        set_terminal_colors,
        setup_unminimize_and_foreground_on_first_print,
    )
    from backend.DONT_CHANGE.scripts._common_variables import (
        CORRECT_START_SIGNAL_FILE_PATH,
        backend_python_exe,
        background_watchdog_path,
    )

    # ==============================
    # define local variables
    # ==============================

    # ==============================
    # define local functions/classes
    # ==============================

    def get_startupinfo(minimized=False):
        """Creates subprocess.Popen STARTUPINFO that opens a child process minimized if minimized, else None (default of Popen)"""
        if minimized:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = getattr(subprocess, "SW_SHOWMINNOACTIVE", 7)
            return startupinfo
        else:
            return None

    # ==============================
    # define main function
    # ==============================

    def main() -> None:

        set_terminal_colors()

        setup_unminimize_and_foreground_on_first_print()

        # ==============================
        # get and process args

        if len(sys.argv) == 3:
            app_id = sys.argv[1]
            launch_mode = sys.argv[2]
        elif len(sys.argv) == 1: # script is run on its own - mode
            app_id = ""
            launch_mode = "terminal"
        else:
            raise ValueError(f"[Error] Wrong number of arguments: {sys.argv}.")

        if launch_mode == "terminal":
            if use_classic_terminal:
                launch_mode = "conhost"
            else:
                launch_mode = "wt"

        # ==============================
        # clear old signal file (signals correct launch of child script)

        try:
            if os.path.exists(CORRECT_START_SIGNAL_FILE_PATH):
                os.remove(CORRECT_START_SIGNAL_FILE_PATH)
        except Exception:
            pass

        # ==============================
        # setup python (I want it here such that install prints are visible even if terminal if set to off and also such that prionts don't stay for final script execution)

        if use_global_python == False:
            # pass app-id in case function is slow and i want taskbar grouping in that time:
            ensure_frontend_packages(app_id)

        # ==============================
        # setup commands for watchdog

        passed_args = [app_id, launch_mode]
        terminal_args = make_empty_args_safe(
            [backend_python_exe, "-X", "faulthandler", background_watchdog_path, *passed_args]
        )

        # ==============================
        # start background watchdog

        if launch_mode == "wt":
            if tab_bar_color:
                terminal_args = ["--tabColor", tab_bar_color] + terminal_args
            process = subprocess.Popen(  # noqa:S603
                ["wt.exe", "--title", program_name, *terminal_args],
                startupinfo=get_startupinfo(start_minimized),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )

        elif launch_mode == "conhost":
            process = subprocess.Popen(  # noqa:S603
                ["conhost.exe", *terminal_args],
                startupinfo=get_startupinfo(start_minimized),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )

        elif launch_mode == "no_terminal":
            process = subprocess.Popen(  # noqa:S603
                terminal_args,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        else:
            raise ValueError(f'[Error] Unknown launch_mode: "{launch_mode}"')

        # ==============================
        # wait for signal file creation to know watchdog had correct start

        for _ in range(100):  # wait up to ~5s
            if os.path.exists(CORRECT_START_SIGNAL_FILE_PATH):
                try:
                    os.remove(CORRECT_START_SIGNAL_FILE_PATH)
                except Exception:
                    pass
                break
            time.sleep(0.05)
        else:
            error_code = process.poll()

            print()
            print_warn("=" * 20)
            print_warn("[Error] Backend code did not seem to launch properly")
            print_warn("-" * 20)
            print_warn(f"Launch mode: {launch_mode}")
            print_warn(f'Error code (potentially meaningless): "{error_code}"')
            try:
                child_output, _ = process.communicate(timeout=0.2)
                if child_output:
                    print_warn("-" * 20)
                    print_warn(child_output.rstrip())
            except Exception:
                pass
            print("=" * 20)
            input_warn("[Error] Press enter to exit")

    # ==============================
    # execute main function
    # ==============================

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            print_traceback(fail_message.format(e=e))
            input_warn("[Error] Press enter to exit")
        close_terminal()

    # =============================

except Exception as e:
    import os
    import traceback

    print()
    print()
    print("=" * 30)
    print(fail_message.format(e=e))
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    input("[Error] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
