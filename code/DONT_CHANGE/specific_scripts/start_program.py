"""WIP"""

# {e} will be formatted to exception:
fail_message = "[Error] Failed to start program: {e}"

try:
    # ==============================
    # import Python packages
    # ==============================

    import os
    import subprocess
    import sys
    import time
    from datetime import datetime

    # ==============================
    # import third-party packages
    # ==============================

    # ==============================
    # imports from files
    # ==============================

    # add root dir to resolve file imports for debug cases where this script is called on its own:
    root_dir = os.path.dirname(__file__) + "\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from developer_settings import (
        classic_terminal_cols,
        classic_terminal_lines,
        close_already_running_instances_on_start,
        enable_log_for_no_terminal_start,
        enable_log_for_Windows_terminal_start,
        log_path_rel_to_start_folder,
        modern_terminal_tab_color,
        prevent_start_if_already_running,
        program_name,
        prompt_to_close_existing_instances,
        start_in_shortcut_folder,
        start_minimized,
        terminal_bg_color,
        terminal_text_color,
        use_classic_terminal,
        use_global_python,
    )
    from DONT_CHANGE.specific_scripts.common_code import (
        close_terminal,
        ensure_frontend_packages,
        get_running_processes_from_pid_file,
        input_warn,
        print_traceback,
        print_warn,
        setup_terminal_colors,
        setup_unminimize_and_foreground_on_first_print,
        stop_processes_from_pid_file,
    )
    from DONT_CHANGE.specific_scripts.common_variables import (
        CORRECT_START_SIGNAL_FILE_PATH,
        EMPTY_ARG_INDICATOR,
        frontend_python_exe,
        process_id_file_path,
        python_script_path,
        script_wrapper_path,
    )

    # ==============================
    # define local variables
    # ==============================

    # ==============================
    # define local functions
    # ==============================

    def make_empty_args_safe(args: list) -> list[str]:
        """Needed because passing empty args as "" in Windows can be flimsy -> replace "" with EMPTY_ARG_INDICATOR and decode in child."""
        return [str(a) if a else EMPTY_ARG_INDICATOR for a in args]

    def generate_minimized_startupinfo():
        """Creates subprocess.Popen STARTUPINFO that opens a child process minimized."""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = getattr(subprocess, "SW_SHOWMINNOACTIVE", 7)
        return startupinfo

    def bool_to_arg(value: bool) -> str:
        """Convert a boolean value to the launcher string argument format."""
        return "true" if value else "false"

    # ==============================
    # define main function
    # ==============================

    def main() -> None:
        # ==============================
        # get args

        if len(sys.argv) == 3:
            app_id = sys.argv[1]
            launch_mode = sys.argv[2]
        elif len(sys.argv) == 1:
            app_id = ""
            launch_mode = "terminal"
        else:
            raise RuntimeError(f"[Error] Wrong number of arguments: {len(sys.argv) - 1}. Allowed 0 or 2.")

        # ==============================
        # process args

        if use_global_python == True:
            python_exe_for_script = "py"
        else:
            python_exe_for_script = frontend_python_exe

        # ==============================
        # set log_path if logging is enabled

        log_path = ""
        if (launch_mode == "terminal" and enable_log_for_Windows_terminal_start == True) or (
            launch_mode == "no_terminal" and enable_log_for_no_terminal_start == True
        ):
            if log_path_rel_to_start_folder:
                if start_in_shortcut_folder == True:
                    log_path = os.path.normpath(os.path.join(os.getcwd(), log_path_rel_to_start_folder))
                else:
                    log_path = os.path.normpath(
                        os.path.join(os.path.dirname(python_script_path), log_path_rel_to_start_folder)
                    )
                log_path = datetime.now().astimezone().strftime(log_path)

        # ==============================
        # clear old signal file (signals correct launch of child script)

        try:
            if os.path.exists(CORRECT_START_SIGNAL_FILE_PATH):
                os.remove(CORRECT_START_SIGNAL_FILE_PATH)
        except Exception:
            pass

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
        # setup python

        if use_global_python == False:
            ensure_frontend_packages(app_id)

        # ==============================
        # setup passed args that all launch modes have in common

        args = [app_id, log_path]

        # ==============================
        # launch main_script in specific launch mode

        if launch_mode in ["terminal", "no_terminal"]:
            if launch_mode == "terminal":
                
                # add terminal appearance to args:
                terminal_colors = ""
                if terminal_bg_color:
                    terminal_colors += terminal_bg_color
                if terminal_text_color:
                    terminal_colors += terminal_text_color
                args += [terminal_colors, classic_terminal_cols, classic_terminal_lines]

                # get terminal launch command:
                if use_classic_terminal:
                    terminal_command = ["conhost.exe"]
                else:  # modern terminal case:
                    terminal_command = ["wt.exe", "--title", program_name]
                    if modern_terminal_tab_color:
                        terminal_command += ["--tabColor", modern_terminal_tab_color]

                startupinfo = generate_minimized_startupinfo() if start_minimized else None
                creationflags = subprocess.CREATE_NEW_CONSOLE
            else:  # no terminal case:
                startupinfo = None
                creationflags = subprocess.CREATE_NO_WINDOW
                terminal_command = []

            terminal_command += [
                python_exe_for_script,
                "-X",
                "faulthandler",
                script_wrapper_path,
                *args,
            ]

            # open new separate process and don't wait:
            process = subprocess.Popen(  # noqa:S603 #type:ignore
                make_empty_args_safe(terminal_command),
                creationflags=creationflags,
                startupinfo=startupinfo,
            )

        else:
            raise ValueError(f'[Error] Unknown launch_mode: "{launch_mode}"')

        # ==============================
        # wait for signal file creation to know that child had correct start

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
            setup_terminal_colors()
            setup_unminimize_and_foreground_on_first_print()
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
